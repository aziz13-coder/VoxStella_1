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

const CLASSICAL_PLANETS = new Set(['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']);
const DIRECTIONAL_PLANETS = new Set([
  ...CLASSICAL_PLANETS,
  'Uranus',
  'Neptune',
  'Pluto',
]);
const SIGN_GLYPHS = ['\u2648', '\u2649', '\u264A', '\u264B', '\u264C', '\u264D', '\u264E', '\u264F', '\u2650', '\u2651', '\u2652', '\u2653'];
const symbolFontFamily = '\'Segoe UI Symbol\', \'Noto Sans Symbols 2\', \'Arial Unicode MS\', sans-serif';
const labelFontFamily = '\'Segoe UI\', system-ui, sans-serif';
const DOME_TILT_RAD = Math.PI / 7.5;
const DOME_PERSPECTIVE = 0.18;
const LABEL_MIN_DISTANCE = 18;
const LABEL_OFFSET_CANDIDATES = [
  [0, 0],
  [0, -16],
  [14, -10],
  [-14, -10],
  [16, 2],
  [-16, 2],
  [12, 14],
  [-12, 14],
  [0, 18],
  [24, -16],
  [-24, -16],
  [24, 16],
  [-24, 16],
];

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
  const numeric = finiteNumberOrUndefined(longitude);
  if (numeric === undefined) return null;
  const totalMinutes = ((Math.round(numeric * 60) % 21600) + 21600) % 21600;
  const signIndex = Math.floor(totalMinutes / 1800);
  const withinSignMinutes = totalMinutes % 1800;
  const degrees = Math.floor(withinSignMinutes / 60);
  const minutes = withinSignMinutes % 60;
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
  if (value === null || value === undefined || typeof value === 'boolean') return undefined;
  if (typeof value === 'string' && value.trim() === '') return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function validCoordinatePair(latitude, longitude) {
  const parsedLatitude = finiteNumberOrUndefined(latitude);
  const parsedLongitude = finiteNumberOrUndefined(longitude);
  if (parsedLatitude === undefined || parsedLongitude === undefined) return null;
  if (parsedLatitude < -90 || parsedLatitude > 90) return null;
  if (parsedLongitude < -180 || parsedLongitude > 180) return null;
  return {
    latitude: parsedLatitude,
    longitude: parsedLongitude,
  };
}

function sanitizePlacement(entry, includeModern) {
  if (!entry || typeof entry !== 'object') return null;
  const planet = String(entry.planet || '').trim();
  const azimuth = finiteNumberOrUndefined(entry.azimuth_deg);
  if (!planet || azimuth === undefined) return null;
  if (!DIRECTIONAL_PLANETS.has(planet)) return null;
  if (!includeModern && !CLASSICAL_PLANETS.has(planet)) return null;
  const altitude = finiteNumberOrUndefined(entry.altitude_deg);
  const validAltitude = altitude !== undefined && altitude >= -90 && altitude <= 90;
  return {
    ...entry,
    planet,
    azimuth_deg: normalizeBearing(azimuth),
    ...(validAltitude ? { altitude_deg: altitude } : { altitude_deg: undefined }),
  };
}

function sanitizePlacements(data, includeModern) {
  if (!Array.isArray(data?.azimuths)) return [];
  return data.azimuths
    .map((entry) => sanitizePlacement(entry, includeModern))
    .filter(Boolean);
}

function payloadHouseCusps(data) {
  const rawCusps = Array.isArray(data?.house_cusps)
    ? data.house_cusps
    : Array.isArray(data?.houses)
      ? data.houses
      : [];
  return rawCusps.map(finiteNumberOrUndefined);
}

function placementContextKey({
  activeSnapId,
  houseSystem,
  includeModern,
  latitude,
  location,
  longitude,
  mode,
  timestamp,
  timezone,
}) {
  return JSON.stringify({
    source: activeSnapId ? `snap:${activeSnapId}` : 'current',
    includeModern: Boolean(includeModern),
    mode: mode === 'manual' ? 'manual' : 'realtime',
    timestamp: timestamp || '',
    location: String(location || '').trim(),
    timezone: String(timezone || '').trim(),
    latitude: latitude ?? null,
    longitude: longitude ?? null,
    houseSystem: houseSystem || '',
  });
}

function snapDashboard(snap) {
  return snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
}

function directionalCoordinatePairFrom(source) {
  if (!source || typeof source !== 'object') return null;
  if (Array.isArray(source.coords) && source.coords.length >= 2) {
    const nested = validCoordinatePair(source.coords[0], source.coords[1]);
    if (nested) return nested;
  }

  const direct = validCoordinatePair(
    source.latitude ?? source.lat,
    source.longitude ?? source.lon ?? source.lng,
  );
  if (direct) return direct;

  const coords = source.coordinates && typeof source.coordinates === 'object' ? source.coordinates : null;
  if (coords) {
    const nested = validCoordinatePair(
      coords.latitude ?? coords.lat,
      coords.longitude ?? coords.lon ?? coords.lng,
    );
    if (nested) return nested;
  }

  const tzCoords = source.timezone_info?.coordinates;
  if (tzCoords && typeof tzCoords === 'object') {
    const nested = validCoordinatePair(
      tzCoords.latitude ?? tzCoords.lat,
      tzCoords.longitude ?? tzCoords.lon ?? tzCoords.lng,
    );
    if (nested) return nested;
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

function directionalSnapHouseSystem(snap) {
  if (!snap || typeof snap !== 'object') return undefined;
  const dashboard = snapDashboard(snap);
  const chartSnapshot = snap?.chart_snapshot && typeof snap.chart_snapshot === 'object'
    ? snap.chart_snapshot
    : {};
  const dashboardChartSnapshot = dashboard?.chart_snapshot
    && typeof dashboard.chart_snapshot === 'object'
    ? dashboard.chart_snapshot
    : {};
  return firstPresent(
    dashboard?.house_system_code,
    snap?.house_system_code,
    chartSnapshot?.house_system_code,
    dashboardChartSnapshot?.house_system_code,
    dashboard?.house_system,
    snap?.house_system,
    chartSnapshot?.house_system,
    dashboardChartSnapshot?.house_system,
  );
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
  const hasCoordinates = latitude !== undefined && longitude !== undefined;
  const hasHouseSystem = directionalSnapHouseSystem(snap) !== undefined;
  return Boolean(snap?.id && (!hasCoordinates || !hasHouseSystem));
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
    houseSystem: firstPresent(directionalSnapHouseSystem(snap), fallbackHouseSystem),
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

function projectPlanPoint(azimuthDeg, radius, cx, cy) {
  const angle = toRadians(90 - normalizeBearing(azimuthDeg));
  const pointRadius = radius;
  return {
    x: cx + pointRadius * Math.cos(angle),
    y: cy - pointRadius * Math.sin(angle),
    pointRadius,
    belowHorizon: false,
    altitudeDeg: null,
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

function distanceBetween(left, right) {
  return Math.hypot(left.x - right.x, left.y - right.y);
}

function labelClearance(point, placed, reserved) {
  const placedClearance = placed.length > 0
    ? Math.min(...placed.map((other) => distanceBetween(point, other) - LABEL_MIN_DISTANCE))
    : Number.POSITIVE_INFINITY;
  const reservedClearance = reserved.length > 0
    ? Math.min(...reserved.map(
      (other) => distanceBetween(point, other) - (other.minDistance || LABEL_MIN_DISTANCE),
    ))
    : Number.POSITIVE_INFINITY;
  return Math.min(placedClearance, reservedClearance);
}

function layoutMarkerLabels(items, size, reserved = []) {
  const placed = [];
  return items.map((item) => {
    const anchor = item.anchor;
    const extendedCandidates = [
      ...LABEL_OFFSET_CANDIDATES,
      ...[28, 36, 44].flatMap((offsetRadius) => (
        Array.from({ length: 12 }, (_value, index) => {
          const angle = (index * Math.PI) / 6;
          return [
            Math.cos(angle) * offsetRadius,
            Math.sin(angle) * offsetRadius,
          ];
        })
      )),
    ];
    const candidates = extendedCandidates
      .map(([dx, dy]) => ({
        x: clamp(anchor.x + dx, 12, size - 12),
        y: clamp(anchor.y + dy, 12, size - 12),
      }));
    const candidate = candidates.find(
      (point) => labelClearance(point, placed, reserved) >= 0,
    ) || candidates.reduce((best, point) => (
      labelClearance(point, placed, reserved) > labelClearance(best, placed, reserved)
        ? point
        : best
    ));
    const label = snapPoint(candidate);
    placed.push(label);
    return {
      ...item,
      label,
      displaced: distanceBetween(anchor, label) > 2,
    };
  });
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
  const [compassRequestState, setCompassRequestState] = useState({
    key: '',
    loading: false,
    error: null,
    data: null,
  });
  const [compassRetryVersion, setCompassRetryVersion] = useState(0);
  const [directional3dOpen, setDirectional3dOpen] = useState(false);
  const [directional3dLoading, setDirectional3dLoading] = useState(false);
  const [directional3dError, setDirectional3dError] = useState(null);
  const [directional3dData, setDirectional3dData] = useState(null);
  const [directional3dSource, setDirectional3dSource] = useState('current');
  const [directional3dSnapId, setDirectional3dSnapId] = useState(activeSnapId || '');
  const [directional3dSnapDetailVersion, setDirectional3dSnapDetailVersion] = useState(0);
  const requestIdRef = useRef(0);
  const directional3dRequestIdRef = useRef(0);
  const directional3dRetryRef = useRef({
    source: 'current',
    snapId: '',
    contextOverride: null,
  });
  const directional3dSnapDetailsRef = useRef(new Map());

  const requestCoordinates = useMemo(
    () => validCoordinatePair(latitude, longitude),
    [latitude, longitude],
  );
  const hasCoordinates = Boolean(requestCoordinates);
  const hasLocation = typeof location === 'string' && location.trim().length > 0;
  const hasRequestContext = Boolean(timestamp && (hasCoordinates || hasLocation));
  const seededData = useMemo(
    () => (Array.isArray(initialData?.azimuths) ? initialData : null),
    [initialData],
  );
  const seededSupportsAltitude = useMemo(
    () => sanitizePlacements(seededData, includeModern)
      .some((item) => finiteNumberOrUndefined(item?.altitude_deg) !== undefined),
    [includeModern, seededData],
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
  const compassBaseHouseSystem = activeCompassSnap ? undefined : houseSystem;
  const compassContextKey = useMemo(
    () => placementContextKey({
      activeSnapId: activeCompassSnap?.id || '',
      houseSystem: compassBaseHouseSystem,
      includeModern,
      latitude: requestCoordinates?.latitude,
      location,
      longitude: requestCoordinates?.longitude,
      mode,
      timestamp,
      timezone,
    }),
    [
      activeCompassSnap?.id,
      compassBaseHouseSystem,
      includeModern,
      location,
      mode,
      requestCoordinates?.latitude,
      requestCoordinates?.longitude,
      timestamp,
      timezone,
    ],
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
    ...(requestCoordinates || {}),
    houseSystem,
  }), [
    houseSystem,
    includeModern,
    location,
    mode,
    requestCoordinates,
    timestamp,
    timezone,
  ]);

  useEffect(() => {
    if (!shouldFetchRemote) {
      setCompassRequestState({
        key: compassContextKey,
        loading: false,
        error: null,
        data: null,
      });
      return undefined;
    }

    let cancelled = false;
    const requestId = ++requestIdRef.current;

    async function fetchCompass() {
      setCompassRequestState({
        key: compassContextKey,
        loading: true,
        error: null,
        data: null,
      });
      try {
        let requestOptions;
        if (activeCompassSnap?.id) {
          const snapKey = String(activeCompassSnap.id);
          let resolvedSnap = mergeDirectionalSnap(
            activeCompassSnap,
            directional3dSnapDetailsRef.current.get(snapKey),
          );
          if (directionalSnapHouseSystem(resolvedSnap) === undefined) {
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
            resolvedSnap = mergeDirectionalSnap(activeCompassSnap, detail);
          }
          const storedHouseSystem = directionalSnapHouseSystem(resolvedSnap);
          requestOptions = {
            includeModern,
            snapId: snapKey,
            ...(storedHouseSystem ? { houseSystem: storedHouseSystem } : {}),
          };
        } else {
          requestOptions = {
            includeModern,
            mode,
            datetime: timestamp,
            location,
            timezone,
            latitude: requestCoordinates?.latitude,
            longitude: requestCoordinates?.longitude,
            houseSystem: compassBaseHouseSystem,
          };
        }
        if (cancelled || requestId !== requestIdRef.current) return;
        const res = await AstroClockAPI.getCompass(requestOptions);
        if (cancelled || requestId !== requestIdRef.current) return;
        if (res?.success) {
          setCompassRequestState({
            key: compassContextKey,
            loading: false,
            error: null,
            data: res.data || null,
          });
        } else {
          setCompassRequestState({
            key: compassContextKey,
            loading: false,
            error: res?.error || 'Failed to load bearings',
            data: null,
          });
        }
      } catch (e) {
        if (cancelled || requestId !== requestIdRef.current) return;
        const msg = String(e?.message || '');
        setCompassRequestState({
          key: compassContextKey,
          loading: false,
          error: msg.includes('license_required') || msg.includes('license_invalid')
            ? 'License required'
            : (msg || 'Failed to load bearings'),
          data: null,
        });
      }
    }

    fetchCompass();
    return () => {
      cancelled = true;
    };
  }, [
    activeCompassSnap,
    compassBaseHouseSystem,
    compassContextKey,
    compassRetryVersion,
    includeModern,
    location,
    mode,
    requestCoordinates?.latitude,
    requestCoordinates?.longitude,
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
        directional3dRetryRef.current = {
          source: 'current',
          snapId: '',
          contextOverride: null,
        };
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
    return snapToDirectionalContext(snap);
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
    const requestedContextOverride = contextOverride && typeof contextOverride === 'object'
      ? { ...contextOverride }
      : null;
    directional3dRetryRef.current = {
      source,
      snapId: String(snapId || ''),
      contextOverride: requestedContextOverride,
    };
    setDirectional3dOpen(true);
    const requestId = ++directional3dRequestIdRef.current;
    setDirectional3dLoading(true);
    setDirectional3dError(null);
    try {
      const loadedSnap = requestedContextOverride
        ? null
        : (source === 'snap' ? await resolveDirectionalSnapForLoad(snapId) : null);
      if (requestId !== directional3dRequestIdRef.current) return;
      const context = requestedContextOverride || resolveDirectionalContext(source, snapId, loadedSnap);
      const requiresDatetime = source === 'snap' || context?.mode === 'manual';
      if (requiresDatetime && !context?.datetime) {
        setDirectional3dData(null);
        setDirectional3dError(source === 'snap'
          ? 'Choose a saved snap with chart time and location.'
          : 'Directional 3D needs an active chart time and location.');
        return;
      }
      const usesStoredSnap = source === 'snap' && !requestedContextOverride && snapId;
      const res = await AstroClockAPI.getDirectional3d(
        usesStoredSnap
          ? {
            includeModern,
            snapId: String(snapId),
            ...(context?.houseSystem ? { houseSystem: context.houseSystem } : {}),
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

  const retryDirectional3d = () => {
    const retry = directional3dRetryRef.current;
    loadDirectional3d(
      retry?.source || directional3dSource,
      retry?.snapId || '',
      retry?.contextOverride ? { ...retry.contextOverride } : null,
    );
  };

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
    const latitudeBase = chartLatitude
      ?? finiteNumberOrUndefined(baseContext.latitude)
      ?? requestCoordinates?.latitude;
    const longitudeBase = chartLongitude
      ?? finiteNumberOrUndefined(baseContext.longitude)
      ?? requestCoordinates?.longitude;
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
    if (activeCompassSnap?.id) {
      const snapId = String(activeCompassSnap.id);
      setDirectional3dSource('snap');
      setDirectional3dSnapId(snapId);
      loadDirectional3d('snap', snapId);
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
      directional3dRetryRef.current = {
        source: 'snap',
        snapId: '',
        contextOverride: null,
      };
      setDirectional3dOpen(true);
      setDirectional3dData(null);
      setDirectional3dError('No saved snaps are available yet.');
    }
  };

  const handleDirectional3dSourceChange = (nextSource) => {
    setDirectional3dSource(nextSource);
    directional3dRetryRef.current = {
      source: nextSource,
      snapId: nextSource === 'snap' ? String(directional3dSnapId || '') : '',
      contextOverride: null,
    };
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
    directional3dRetryRef.current = {
      source: 'snap',
      snapId: nextSnapId,
      contextOverride: null,
    };
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

  const compassStateMatchesContext = compassRequestState.key === compassContextKey;
  const remoteData = compassStateMatchesContext ? compassRequestState.data : null;
  const loading = shouldFetchRemote && (
    !compassStateMatchesContext || compassRequestState.loading
  );
  const error = compassStateMatchesContext ? compassRequestState.error : null;
  const displayData = activeCompassSnap ? remoteData : (remoteData || seededData);
  const placements = useMemo(
    () => sanitizePlacements(displayData, includeModern),
    [displayData, includeModern],
  );
  const hasDisplayData = placements.length > 0;
  const altitudePlacements = useMemo(
    () => placements.filter(
      (item) => finiteNumberOrUndefined(item?.altitude_deg) !== undefined,
    ),
    [placements],
  );
  const supportsAltitude = altitudePlacements.length > 0;
  const activeView = view === 'alt' && supportsAltitude ? 'alt' : 'az';
  const plottedPlacements = activeView === 'alt' ? altitudePlacements : placements;
  const missingAltitudeCount = activeView === 'alt'
    ? placements.length - altitudePlacements.length
    : 0;
  const displayCusps = useMemo(() => {
    const payloadCusps = payloadHouseCusps(displayData);
    if (payloadCusps.length > 0) return payloadCusps;
    if (activeCompassSnap) return [];
    return Array.isArray(houseCusps) ? houseCusps.map(finiteNumberOrUndefined) : [];
  }, [activeCompassSnap, displayData, houseCusps]);
  const payloadCusps = useMemo(() => payloadHouseCusps(displayData), [displayData]);
  const payloadAscendant = finiteNumberOrUndefined(displayData?.ascendant);
  const displayAscendant = firstPresent(
    payloadAscendant,
    displayCusps[0],
  );
  const displayDescendant = firstPresent(
    finiteNumberOrUndefined(displayData?.descendant),
    payloadCusps[6],
    payloadAscendant === undefined ? displayCusps[6] : undefined,
    displayAscendant === undefined ? undefined : normalizeBearing(displayAscendant + 180),
  );
  const risingLabel = useMemo(
    () => formatZodiacPoint(displayAscendant),
    [displayAscendant],
  );
  const settingLabel = useMemo(
    () => formatZodiacPoint(displayDescendant),
    [displayDescendant],
  );
  const bodyScopeLabel = includeModern
    ? 'Traditional and modern bodies'
    : 'Traditional bodies';
  const chartSourceLabel = activeCompassSnap
    ? (activeCompassSnap.label || 'Saved chart')
    : 'Current chart';

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
        : projectPlanPoint(entry?.azimuth_deg, radius * 0.82, cx, cy)
    );
    const zenithPoint = snapPoint(projectDomePoint(0, 90, radius, cx, cy));
    const cardinalPoints = ['N', 'E', 'S', 'W'].map((cardinal, index) => ({
      cardinal,
      point: snapPoint(
        isDomeView
          ? projectDomePoint(index * 90, 0, radius + 10, cx, cy)
          : projectPlanPoint(index * 90, radius + 14, cx, cy),
      ),
    }));
    const referenceReservations = [
      ...cardinalPoints.map(({ point }) => ({
        x: point.x,
        y: point.y,
        minDistance: 15,
      })),
      ...(isDomeView
        ? [
          { x: zenithPoint.x, y: zenithPoint.y, minDistance: 16 },
          { x: zenithPoint.x, y: zenithPoint.y - 8, minDistance: 15 },
        ]
        : []),
    ];

    const ordered = [...plottedPlacements]
      .map((entry, index) => ({ entry, index }))
      .sort((a, b) => {
        const bearingDelta = normalizeBearing(a.entry?.azimuth_deg) - normalizeBearing(b.entry?.azimuth_deg);
        if (bearingDelta !== 0) return bearingDelta;
        const planetDelta = String(a.entry?.planet || '').localeCompare(String(b.entry?.planet || ''));
        return planetDelta || a.index - b.index;
      });
    const markerLayouts = layoutMarkerLabels(
      ordered.map((item) => ({
        ...item,
        anchor: snapPoint(projectPoint(item.entry)),
      })),
      size,
      referenceReservations,
    );
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
    const renderedEntries = isDomeView
      ? [...markerLayouts].sort((left, right) => {
        const leftDepth = left.anchor?.depth ?? 0;
        const rightDepth = right.anchor?.depth ?? 0;
        return rightDepth - leftDepth;
      })
      : markerLayouts;

    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox={`0 0 ${size} ${size}`}
        className="block h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
        shapeRendering="geometricPrecision"
        textRendering="optimizeLegibility"
        role="img"
        aria-label={isDomeView
          ? 'Altitude sky-dome plot of directional bodies'
          : 'Azimuth bearing-only compass plot of directional bodies'}
        data-directional-plot={isDomeView ? 'altitude' : 'azimuth'}
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
            <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#d4d4d8" strokeWidth="1" />
            <line x1={cx - radius} y1={cy} x2={cx + radius} y2={cy} stroke="#eceef2" strokeDasharray="3 4" />
            <line x1={cx} y1={cy - radius} x2={cx} y2={cy + radius} stroke="#f1f3f6" strokeDasharray="3 4" />
          </>
        )}
        {isDomeView ? (
          <>
            <circle
              cx={zenithPoint.x}
              cy={zenithPoint.y}
              r={3}
              fill="#111827"
              data-directional-zenith-anchor=""
            />
            <text
              x={snapCoord(zenithPoint.x)}
              y={snapCoord(zenithPoint.y - 8)}
              fontSize="9"
              textAnchor="middle"
              fill="#a1a1aa"
              style={{ fontFamily: labelFontFamily }}
              data-directional-reference-label="Z"
            >
              Z
            </text>
          </>
        ) : (
          <circle cx={cx} cy={cy} r={2} fill="#a1a1aa" />
        )}
        {cardinalPoints.map(({ cardinal, point }) => (
            <text
              key={cardinal}
              x={snapCoord(point.x)}
              y={snapCoord(point.y)}
              fontSize="11"
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#6b7280"
              style={{ fontFamily: labelFontFamily }}
              data-directional-reference-label={cardinal}
            >
              {cardinal}
            </text>
        ))}
        {renderedEntries.map(({ anchor, displaced, entry, index, label }) => {
          const belowHorizon = !!anchor.belowHorizon;
          const symbol = PlanetSymbols[entry.planet] || entry.planet;
          return (
            <g key={`${entry.planet}-${index}`} opacity={belowHorizon ? 0.72 : 1}>
              <title>
                {`${entry.planet || 'Planet'} at ${normalizeBearing(entry.azimuth_deg).toFixed(1)} degrees azimuth${
                  isDomeView ? ` and ${Number(entry.altitude_deg).toFixed(1)} degrees altitude` : ''
                }`}
              </title>
              <circle
                cx={anchor.x}
                cy={anchor.y}
                r="1.75"
                fill={belowHorizon ? '#6b7280' : '#111827'}
                data-directional-anchor={entry.planet}
                data-bearing={normalizeBearing(entry.azimuth_deg)}
              />
              {displaced ? (
                <line
                  x1={anchor.x}
                  y1={anchor.y}
                  x2={label.x}
                  y2={label.y}
                  stroke="#a1a1aa"
                  strokeWidth="0.8"
                  data-directional-leader={entry.planet}
                />
              ) : null}
              <text
                x={label.x}
                y={label.y}
                fontSize={isDomeView ? '15' : '14'}
                fontWeight="600"
                textAnchor="middle"
                dominantBaseline="middle"
                fill={belowHorizon ? '#6b7280' : '#111827'}
                stroke="rgba(255,255,255,0.94)"
                strokeWidth="3.2"
                paintOrder="stroke"
                style={{ fontFamily: symbolFontFamily }}
                data-directional-label={entry.planet}
              >
                {symbol}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }, [activeView, hasDisplayData, plottedPlacements, supportsAltitude]);

  const emptyMessage = activeCompassSnap
    ? 'No local-space bearings returned for this saved chart.'
    : !hasRequestContext
      ? (hasCoordinates ? 'Waiting for a chart timestamp.' : 'Set a chart location to render local-space bearings.')
      : 'No local-space bearings returned for this chart.';
  const directional3dChartInfo = directional3dData?.chart_info || {};
  const canStepDirectionalTime = directional3dSource === 'snap'
    || currentDirectionalContext.mode === 'manual'
    || Boolean(firstPresent(directional3dChartInfo.utc_datetime, currentDirectionalContext.datetime, timestamp));

  return (
    <>
    <div
      className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm"
      aria-busy={loading}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400">
            Directional
          </div>
          <div className="mt-1 truncate text-[10px] text-zinc-500" title={`${chartSourceLabel} · ${bodyScopeLabel}`}>
            {chartSourceLabel} · {bodyScopeLabel}
          </div>
        </div>
        <div
          className="inline-flex shrink-0 rounded-full border border-zinc-200 bg-white p-1"
          role="group"
          aria-label="Directional view"
        >
          {[
            { key: 'az', label: 'Az', disabled: false },
            { key: 'alt', label: 'Alt', disabled: !supportsAltitude },
          ].map((option) => (
            <button
              key={option.key}
              type="button"
              disabled={option.disabled}
              onClick={() => setView(option.key)}
              aria-pressed={activeView === option.key}
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
            aria-expanded={directional3dOpen}
            aria-haspopup="dialog"
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

      <div className="mt-3 text-[11px] text-zinc-500" aria-live="polite">
        {activeView === 'alt'
          ? 'Altitude · position above or below the local horizon'
          : 'Azimuth · compass bearing only'}
      </div>

      <div className="mt-4">
        {error && !hasDisplayData ? (
          <div
            className="flex min-h-[280px] flex-col items-center justify-center gap-3 text-center text-sm text-red-600"
            role="alert"
          >
            <span>{error}</span>
            <button
              type="button"
              onClick={() => setCompassRetryVersion((version) => version + 1)}
              className="rounded-full border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50"
            >
              Retry bearings
            </button>
          </div>
        ) : null}
        {!error && !hasDisplayData && loading ? (
          <div
            className="flex min-h-[280px] items-center justify-center text-sm text-zinc-500"
            role="status"
            aria-live="polite"
          >
            Updating local-space bearings...
          </div>
        ) : null}
        {!error && !hasDisplayData && !loading ? (
          <div
            className="flex min-h-[280px] items-center justify-center text-center text-sm text-zinc-500"
            role="status"
          >
            {emptyMessage}
          </div>
        ) : null}
        {hasDisplayData ? (
          <>
            <div className="mx-auto w-full max-w-[276px]">{svg}</div>
            <ul className="sr-only" aria-label="Directional body positions">
              {plottedPlacements.map((entry, index) => (
                <li key={`${entry.planet}-description-${index}`}>
                  {entry.planet}: {normalizeBearing(entry.azimuth_deg).toFixed(1)} degrees azimuth
                  {activeView === 'alt'
                    ? `, ${Number(entry.altitude_deg).toFixed(1)} degrees altitude`
                    : ''}
                </li>
              ))}
            </ul>
            {missingAltitudeCount > 0 ? (
              <div className="mt-1 text-center text-[10px] text-zinc-500" role="status">
                {missingAltitudeCount} {missingAltitudeCount === 1 ? 'body is' : 'bodies are'} omitted because altitude is unavailable.
              </div>
            ) : null}
          </>
        ) : null}
      </div>

      {hasDisplayData ? (
        <>
          <div className="mt-2 grid grid-cols-2 gap-3 border-t border-zinc-100 pt-3">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                Ascendant
              </div>
              <div className="mt-1 text-[1rem] font-medium text-zinc-900">
                {risingLabel || '\u2014'}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                Descendant
              </div>
              <div className="mt-1 text-[1rem] font-medium text-zinc-900">
                {settingLabel || '\u2014'}
              </div>
            </div>
          </div>
          {error && hasDisplayData ? (
            <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-amber-700" role="alert">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setCompassRetryVersion((version) => version + 1)}
                className="shrink-0 rounded-full border border-amber-200 bg-white px-2.5 py-1 font-semibold hover:bg-amber-50"
              >
                Retry bearings
              </button>
            </div>
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
      onRetry={retryDirectional3d}
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
