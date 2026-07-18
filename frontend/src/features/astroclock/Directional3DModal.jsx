import React, { useEffect, useMemo, useState } from 'react';
import {
  formatSavedSnapDateTime,
  formatSavedSnapLabel,
  getSavedSnapIneligibilityLabel,
  isSavedSnapCalculationEligible,
} from './savedSnapViewModel.mjs';

const SYSTEMS = ['EQL', 'EQU', 'HOR'];
const SYSTEM_COLORS = {
  EQL: '#111827',
  EQU: '#0f766e',
  HOR: '#b45309',
};
const SYSTEM_DETAILS = {
  EQL: {
    label: 'EQL',
    name: 'Ecliptic',
    longitudeLabel: 'Lon',
    latitudeLabel: 'Lat',
  },
  EQU: {
    label: 'EQU',
    name: 'Equatorial',
    longitudeLabel: 'RA',
    latitudeLabel: 'Dec',
  },
  HOR: {
    label: 'HOR',
    name: 'Horizon',
    longitudeLabel: 'Az',
    latitudeLabel: 'Alt',
  },
};
const OBJECT_COLORS = {
  Sun: '#f59e0b',
  Moon: '#64748b',
  Mercury: '#0f766e',
  Venus: '#be123c',
  Mars: '#ef4444',
  Jupiter: '#7c3aed',
  Saturn: '#27272a',
  Uranus: '#0891b2',
  Neptune: '#2563eb',
  Pluto: '#6d28d9',
  Chiron: '#475569',
  'North Node': '#334155',
  'South Node': '#334155',
};
const OBJECT_SYMBOLS = {
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
  Chiron: '\u26B7',
  'North Node': '\u260A',
  'South Node': '\u260B',
};
const LAYER_PRESETS = {
  EQL: { objects: true, ecliptic: true, equator: false, horizon: false, tropics: true, polarCircles: true, axes: true, houses: true, hiddenHalf: true },
  EQU: { objects: true, ecliptic: false, equator: true, horizon: false, tropics: true, polarCircles: true, axes: true, houses: false, hiddenHalf: true },
  HOR: { objects: true, ecliptic: false, equator: false, horizon: true, tropics: false, polarCircles: false, axes: true, houses: false, hiddenHalf: true },
  ALL: { objects: true, ecliptic: true, equator: true, horizon: true, tropics: true, polarCircles: true, axes: true, houses: true, hiddenHalf: true },
};
const LAYER_LABELS = [
  ['objects', 'Objects'],
  ['ecliptic', 'Ecliptic'],
  ['equator', 'Equator'],
  ['horizon', 'Horizon'],
  ['tropics', 'Tropics'],
  ['polarCircles', 'Polar'],
  ['axes', 'Axes'],
  ['houses', 'Houses'],
  ['hiddenHalf', 'Back half'],
];

function toNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function toRadians(degrees) {
  return (degrees * Math.PI) / 180;
}

function normalizeDegrees(degrees) {
  const value = toNumber(degrees);
  const wrapped = value % 360;
  return wrapped < 0 ? wrapped + 360 : wrapped;
}

function formatNumber(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '--';
  return number.toFixed(digits);
}

function formatCoordinate(coord, showLatitude = true) {
  if (!coord) return '--';
  return `${formatNumber(coord.longitude)} / ${showLatitude ? formatNumber(coord.latitude) : '--'}`;
}

function firstPresent(...values) {
  for (const value of values) {
    if (value === null || value === undefined) continue;
    const text = String(value).trim();
    if (text) return value;
  }
  return undefined;
}

function snapDashboard(snap) {
  return snap?.dashboard && typeof snap.dashboard === 'object' ? snap.dashboard : {};
}

function getSnapParts(snap) {
  const dashboard = snapDashboard(snap);
  const label = String(firstPresent(snap?.label, snap?.id, 'Untitled snap') || 'Untitled snap').trim();
  const location = String(firstPresent(snap?.location, dashboard?.location, '') || '').trim();
  const timezone = String(firstPresent(snap?.timezone, dashboard?.timezone, snap?.timezone_label, dashboard?.timezone_label, '') || '').trim();
  return {
    label,
    stamp: formatSavedSnapDateTime(snap),
    location,
    timezone,
  };
}

function formatSnapLabel(snap) {
  return formatSavedSnapLabel(snap);
}

function safeObjectSymbol(item) {
  if (!item) return '';
  const mapped = OBJECT_SYMBOLS[item.name];
  if (mapped) return mapped;
  const symbol = String(item.symbol || '').trim();
  if (symbol && !symbol.includes('\uFFFD') && !/[ÃÂâ]/.test(symbol)) return symbol;
  return String(item.name || '?').slice(0, 2).trim() || '?';
}

function isCuspObject(item) {
  return item?.object_type === 'cusp' || item?.bfull === false;
}

function objectAccentColor(item, fallback) {
  return OBJECT_COLORS[item?.name] || fallback || '#111827';
}

function atan2Like(x, y) {
  if (x === 0) return y >= 0 ? 90 : 270;
  if (y === 0) return x >= 0 ? 0 : 180;
  return normalizeDegrees((Math.atan2(y, x) * 180) / Math.PI);
}

function rotateSpherical(longitude, latitude, rotationDeg) {
  const lon = toRadians(normalizeDegrees(longitude));
  const lat = toRadians(toNumber(latitude));
  const rotation = toRadians(rotationDeg);
  const cosLat = Math.cos(lat);
  const x = cosLat * Math.cos(lon);
  const y = cosLat * Math.sin(lon);
  const z = Math.sin(lat);
  const rotatedY = (y * Math.cos(rotation)) - (z * Math.sin(rotation));
  const rotatedZ = (y * Math.sin(rotation)) + (z * Math.cos(rotation));
  return {
    longitude: atan2Like(x, rotatedY),
    latitude: (Math.asin(Math.max(-1, Math.min(1, rotatedZ))) * 180) / Math.PI,
  };
}

function finalProject(longitude, latitude, rotation, tilt, radiusX, radiusY, center) {
  let workingLongitude = normalizeDegrees(270 - (toNumber(longitude) + toNumber(rotation)));
  let workingLatitude = toNumber(latitude);
  if (toNumber(tilt) !== 0) {
    const rotated = rotateSpherical(workingLongitude, workingLatitude, tilt);
    workingLongitude = rotated.longitude;
    workingLatitude = rotated.latitude;
  }
  const lonRad = toRadians(workingLongitude);
  const latRad = toRadians(workingLatitude);
  return {
    x: center + (radiusX * Math.cos(lonRad) * Math.cos(latRad)),
    y: center + (radiusY * Math.sin(latRad)),
    hidden: workingLongitude >= 180,
    depth: Math.cos(lonRad) * Math.cos(latRad),
  };
}

function projectCoordinate(coord, system, rotation, tilt, radiusX, radiusY, center, obliquity) {
  const longitude = toNumber(coord?.longitude);
  const latitude = toNumber(coord?.latitude);
  if (system === 'HOR') {
    const rotated = rotateSpherical(longitude, latitude, -90);
    return finalProject(rotated.longitude, rotated.latitude, rotation, tilt, radiusX, radiusY, center);
  }
  const base = system === 'EQL'
    ? rotateSpherical(longitude, latitude, obliquity)
    : { longitude, latitude };
  const viewLongitude = normalizeDegrees(0 - base.longitude + 90);
  const viewRelative = rotateSpherical(viewLongitude, base.latitude, 90);
  return finalProject(viewRelative.longitude, viewRelative.latitude, rotation, tilt, radiusX, radiusY, center);
}

function buildSystemCirclePath(system, kind, rotation, tilt, radiusX, radiusY, center, obliquity) {
  const points = [];
  for (let step = 0; step <= 360; step += 8) {
    const coord = kind === 'vertical'
      ? {
        longitude: step <= 180 ? 0 : 180,
        latitude: step <= 180 ? step - 90 : 270 - step,
      }
      : { longitude: step, latitude: 0 };
    const projected = projectCoordinate(coord, system, rotation, tilt, radiusX, radiusY, center, obliquity);
    points.push(`${step === 0 ? 'M' : 'L'} ${projected.x.toFixed(2)} ${projected.y.toFixed(2)}`);
  }
  return points.join(' ');
}

function buildLatitudeCirclePath(system, latitude, rotation, tilt, radiusX, radiusY, center, obliquity) {
  const points = [];
  for (let step = 0; step <= 360; step += 8) {
    const projected = projectCoordinate({ longitude: step, latitude }, system, rotation, tilt, radiusX, radiusY, center, obliquity);
    points.push(`${step === 0 ? 'M' : 'L'} ${projected.x.toFixed(2)} ${projected.y.toFixed(2)}`);
  }
  return points.join(' ');
}

function buildHouseBoundaryPath(cusp, rotation, tilt, radiusX, radiusY, center, obliquity) {
  const longitude = normalizeDegrees(cusp?.EQL?.longitude);
  const points = [];
  for (let latitude = -86; latitude <= 86; latitude += 6) {
    const projected = projectCoordinate({ longitude, latitude }, 'EQL', rotation, tilt, radiusX, radiusY, center, obliquity);
    points.push(`${points.length === 0 ? 'M' : 'L'} ${projected.x.toFixed(2)} ${projected.y.toFixed(2)}`);
  }
  return points.join(' ');
}

function CoordinateReadout({ label, value, muted = false }) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400">
        {label}
      </div>
      <div className={`mt-1 text-sm font-semibold tabular-nums ${muted ? 'text-zinc-400' : 'text-zinc-950'}`}>
        {muted ? '--' : formatNumber(value)}
      </div>
    </div>
  );
}

function CoordinateSystemPanel({ item, system }) {
  const details = SYSTEM_DETAILS[system] || SYSTEM_DETAILS.EQL;
  const coord = item?.[system] || {};
  const hasFullLatitude = item?.bfull !== false;
  const showLatitudeSpeed = system === 'EQU' || system === 'HOR';

  return (
    <div data-directional-coordinate-panel={system} className="min-w-0 p-3 sm:p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-400">
            {details.label}
          </div>
          <div className="mt-1 truncate text-sm font-semibold text-zinc-950">
            {details.name}
          </div>
        </div>
        <span
          aria-hidden="true"
          className="mt-1 h-2 w-2 flex-none rounded-full"
          style={{ backgroundColor: SYSTEM_COLORS[system] || '#111827' }}
        />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <CoordinateReadout label={details.longitudeLabel} value={coord.longitude} />
        <CoordinateReadout label={details.latitudeLabel} value={coord.latitude} muted={!hasFullLatitude} />
      </div>

      <div className="mt-3 space-y-2 border-t border-zinc-100 pt-3 text-[11px] text-zinc-500">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium text-zinc-700">Speed {formatNumber(coord.speed, 3)}</span>
          <span className="text-zinc-400">deg/day</span>
        </div>
        {showLatitudeSpeed ? (
          <div className="flex items-center justify-between gap-3">
            <span className="font-medium text-zinc-700">Lat speed {formatNumber(coord.latitude_speed, 3)}</span>
            <span className="text-zinc-400">deg/day</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function InspectorMetric({ label, children }) {
  return (
    <div className="min-w-0 p-3 sm:p-4">
      <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-400">
        {label}
      </div>
      <div className="mt-1 min-w-0 text-sm font-semibold text-zinc-950">
        {children}
      </div>
    </div>
  );
}

function DirectionalInspector({ activeSystems, objectsCount, payloadSystems, selectedObject }) {
  const selectedAccent = objectAccentColor(selectedObject);
  const systemsLabel = payloadSystems?.length ? payloadSystems.join(' / ') : SYSTEMS.join(' / ');
  const selectedIsCusp = isCuspObject(selectedObject);

  return (
    <section
      data-directional-inspector=""
      className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm"
      aria-label="Directional object inspector"
    >
      <div className="grid divide-y divide-zinc-100 sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        <InspectorMetric label="Active view">
          <span className="truncate">{activeSystems.join(' + ')}</span>
        </InspectorMetric>
        <InspectorMetric label="Objects">
          <span className="tabular-nums">{objectsCount}</span>
        </InspectorMetric>
        <InspectorMetric label="Selected object">
          {selectedObject ? (
            <span className="flex min-w-0 items-center gap-2">
              {!selectedIsCusp ? (
                <span
                  aria-hidden="true"
                  className="text-lg leading-none"
                  style={{
                    color: selectedAccent,
                    textShadow: `0 0 10px ${selectedAccent}55`,
                  }}
                >
                  {safeObjectSymbol(selectedObject)}
                </span>
              ) : null}
              <span className="truncate">{selectedObject.name}</span>
            </span>
          ) : (
            'None'
          )}
        </InspectorMetric>
        <InspectorMetric label="Systems">
          <span className="truncate">{systemsLabel}</span>
        </InspectorMetric>
      </div>

      {selectedObject ? (
        <div className="grid divide-y divide-zinc-100 border-t border-zinc-100 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          {SYSTEMS.map((itemSystem) => (
            <CoordinateSystemPanel key={itemSystem} item={selectedObject} system={itemSystem} />
          ))}
        </div>
      ) : (
        <div className="border-t border-zinc-100 p-4 text-sm text-zinc-500">
          Select an object to inspect its coordinates.
        </div>
      )}
    </section>
  );
}

function SortButton({ active, direction, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left text-[10px] font-semibold uppercase tracking-[0.12em] ${
        active ? 'text-zinc-950' : 'text-zinc-500'
      }`}
    >
      {children}{active ? (direction === 'asc' ? ' \u2191' : ' \u2193') : ''}
    </button>
  );
}

function DirectionalSphere({
  objects,
  system,
  rotation,
  tilt,
  layers,
  obliquity,
  selectedId,
  onSelect,
}) {
  const size = 320;
  const center = size / 2;
  const radiusX = 126;
  const radiusY = 118;
  const activeSystems = system === 'ALL' ? SYSTEMS : [system];
  const projectedRows = useMemo(() => {
    const rows = [];
    for (const activeSystem of activeSystems) {
      for (const item of objects) {
        if (item?.object_type === 'cusp' || item?.bfull === false) continue;
        const coord = item?.[activeSystem];
        if (!coord) continue;
        const point = projectCoordinate(coord, activeSystem, rotation, tilt, radiusX, radiusY, center, obliquity);
        rows.push({ item, system: activeSystem, point });
      }
    }
    return rows.sort((left, right) => left.point.depth - right.point.depth);
  }, [activeSystems, center, objects, obliquity, radiusX, radiusY, rotation, tilt]);

  const layerPaths = useMemo(() => {
    const paths = [];
    if (layers.ecliptic) {
      paths.push({
        key: 'ecliptic',
        system: 'EQL',
        stroke: SYSTEM_COLORS.EQL,
        label: 'Ecliptic',
        dash: '',
      });
    }
    if (layers.equator) {
      paths.push({
        key: 'equator',
        system: 'EQU',
        stroke: SYSTEM_COLORS.EQU,
        label: 'Equator',
        dash: '5 4',
      });
    }
    if (layers.horizon) {
      paths.push({
        key: 'horizon',
        system: 'HOR',
        stroke: SYSTEM_COLORS.HOR,
        label: 'Horizon',
        dash: '2 4',
      });
    }
    return paths;
  }, [layers.ecliptic, layers.equator, layers.horizon]);
  const referencePaths = useMemo(() => {
    const paths = [];
    const axialTilt = Math.abs(toNumber(obliquity, 23.439291));
    if (layers.tropics) {
      paths.push(
        { key: 'tropic-north', type: 'tropic', latitude: axialTilt, stroke: '#14b8a6', dash: '6 5', opacity: 0.45 },
        { key: 'tropic-south', type: 'tropic', latitude: -axialTilt, stroke: '#14b8a6', dash: '6 5', opacity: 0.45 },
      );
    }
    if (layers.polarCircles) {
      const polarLatitude = 90 - axialTilt;
      paths.push(
        { key: 'polar-north', type: 'polar', latitude: polarLatitude, stroke: '#71717a', dash: '2 5', opacity: 0.36 },
        { key: 'polar-south', type: 'polar', latitude: -polarLatitude, stroke: '#71717a', dash: '2 5', opacity: 0.36 },
      );
    }
    return paths;
  }, [layers.polarCircles, layers.tropics, obliquity]);
  const houseCusps = useMemo(
    () => objects.filter((item) => item.object_type === 'cusp' || item.bfull === false),
    [objects],
  );

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className="h-auto w-full"
      role="img"
      aria-label="Directional 3D chart"
      shapeRendering="geometricPrecision"
      textRendering="optimizeLegibility"
    >
      <defs>
        <filter id="directional-selected-glow" x="-90%" y="-90%" width="280%" height="280%">
          <feDropShadow dx="0" dy="0" stdDeviation="2.2" floodColor="currentColor" floodOpacity="0.82" />
          <feDropShadow dx="0" dy="0" stdDeviation="5.8" floodColor="currentColor" floodOpacity="0.42" />
        </filter>
      </defs>
      <ellipse cx={center} cy={center} rx={radiusX} ry={radiusY} fill="#fafafa" stroke="#d4d4d8" strokeWidth="1.5" />
      {layerPaths.map((path) => (
        <g key={path.key}>
          <path
            d={buildSystemCirclePath(path.system, 'horizontal', rotation, tilt, radiusX, radiusY, center, obliquity)}
            fill="none"
            stroke={path.stroke}
            strokeDasharray={path.dash}
            strokeWidth="1.2"
            opacity="0.72"
          />
        </g>
      ))}
      {referencePaths.map((path) => (
        <path
          key={path.key}
          data-directional-reference={path.type}
          d={buildLatitudeCirclePath('EQU', path.latitude, rotation, tilt, radiusX, radiusY, center, obliquity)}
          fill="none"
          stroke={path.stroke}
          strokeDasharray={path.dash}
          strokeWidth="0.9"
          opacity={path.opacity}
        />
      ))}
      {layers.axes ? activeSystems.map((activeSystem) => (
        <path
          key={`${activeSystem}-axis`}
          d={buildSystemCirclePath(activeSystem, 'vertical', rotation, tilt, radiusX, radiusY, center, obliquity)}
          fill="none"
          stroke={SYSTEM_COLORS[activeSystem] || '#71717a'}
          strokeDasharray="4 6"
          strokeWidth="0.9"
          opacity="0.45"
        />
      )) : null}
      {layers.houses ? houseCusps.map((item, index) => {
        const boundaryPath = buildHouseBoundaryPath(item, rotation, tilt, radiusX, radiusY, center, obliquity);
        const angularHouse = ['House 1', 'House 4', 'House 7', 'House 10'].includes(item.name);
        return (
          <path
            key={`house-boundary-${item.object_id}`}
            data-directional-house-boundary=""
            d={boundaryPath}
            fill="none"
            stroke={angularHouse ? '#3f3f46' : '#a1a1aa'}
            strokeWidth={angularHouse ? '1.35' : '0.85'}
            strokeDasharray={angularHouse ? '' : '3 5'}
            opacity={angularHouse ? '0.68' : '0.42'}
          />
        );
      }) : null}
      {layers.houses ? houseCusps.map((item) => {
        const point = projectCoordinate(item.EQL, 'EQL', rotation, tilt, radiusX, radiusY, center, obliquity);
        if (point.hidden && !layers.hiddenHalf) return null;
        const selected = selectedId === item.object_id;
        const fill = selected ? '#18181b' : '#52525b';
        return (
          <g
            key={`house-label-${item.object_id}`}
            role="button"
            tabIndex="0"
            aria-label={`${item.name} EQL`}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => onSelect(item)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') onSelect(item);
            }}
            opacity={point.hidden ? 0.28 : 0.78}
            className="cursor-pointer"
            style={{ outline: 'none' }}
          >
            <text
              data-directional-selected-object={selected ? item.object_id : undefined}
              x={point.x}
              y={point.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={selected ? '9.5' : '8.5'}
              fontWeight="800"
              fill={fill}
              color={fill}
              filter={selected ? 'url(#directional-selected-glow)' : undefined}
              paintOrder={selected ? undefined : 'stroke'}
              stroke={selected ? 'none' : '#ffffff'}
              strokeWidth={selected ? '0' : '3'}
              strokeLinejoin="round"
              style={{ fontFamily: 'Inter, Segoe UI, system-ui, sans-serif', letterSpacing: '0' }}
            >
              {item.symbol}
            </text>
          </g>
        );
      }) : null}
      {layers.objects ? projectedRows.map(({ item, system: rowSystem, point }) => {
        if (point.hidden && !layers.hiddenHalf) return null;
        const selected = selectedId === item.object_id;
        const color = SYSTEM_COLORS[rowSystem] || '#111827';
        const isCusp = isCuspObject(item);
        const accentColor = selected ? objectAccentColor(item, color) : color;
        const labelSize = isCusp ? 9.5 : (selected ? 18 : 15);
        const symbol = safeObjectSymbol(item);
        return (
          <g
            key={`${rowSystem}-${item.object_id}`}
            role="button"
            tabIndex="0"
            aria-label={`${item.name} ${rowSystem}`}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => onSelect(item)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') onSelect(item);
            }}
            opacity={point.hidden ? 0.38 : 1}
            className="cursor-pointer"
            style={{ outline: 'none' }}
          >
            <text
              data-directional-selected-object={selected ? item.object_id : undefined}
              x={point.x}
              y={point.y + (isCusp ? 0.25 : 0.5)}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={String(labelSize)}
              fontWeight={selected ? '800' : '700'}
              fill={accentColor}
              color={accentColor}
              filter={selected ? 'url(#directional-selected-glow)' : undefined}
              paintOrder={selected ? undefined : 'stroke'}
              stroke={selected ? 'none' : '#ffffff'}
              strokeWidth={selected ? '0' : (isCusp ? '2.6' : '3.4')}
              strokeLinejoin="round"
              style={{ fontFamily: isCusp ? 'Inter, Segoe UI, system-ui, sans-serif' : 'Georgia, Cambria, Times New Roman, serif' }}
            >
              {symbol}
            </text>
          </g>
        );
      }) : null}
    </svg>
  );
}

function DirectionalSourceBar({
  chartSource,
  currentSourceLabel,
  onChartSourceChange,
  snapOptions,
  selectedSnapId,
  selectedSnap,
  onSnapChange,
  loadingSnaps,
  snapsLoaded,
  onRefreshSnaps,
}) {
  const eligibleSnapOptions = (Array.isArray(snapOptions) ? snapOptions : []).filter(
    (snap) => isSavedSnapCalculationEligible(snap),
  );
  const hasSnaps = eligibleSnapOptions.length > 0;
  const hasReviewRequiredSnaps = (Array.isArray(snapOptions) ? snapOptions : []).some(
    (snap) => !isSavedSnapCalculationEligible(snap),
  );
  const selectedParts = getSnapParts(selectedSnap);
  const snapMessage = loadingSnaps
    ? 'Loading saved snaps...'
    : !snapsLoaded
      ? 'Refresh saved snaps'
      : !hasSnaps
        ? 'No saved snaps'
        : 'Select a saved snap';
  return (
    <div className="border-b border-zinc-200 bg-white px-5 py-3">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
            Chart Source
          </span>
          <button
            type="button"
            aria-pressed={chartSource === 'current'}
            onClick={() => onChartSourceChange?.('current')}
            className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] ${
              chartSource === 'current'
                ? 'border-zinc-900 bg-zinc-900 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-950'
            }`}
          >
            {currentSourceLabel || 'Current'}
          </button>
          <button
            type="button"
            aria-pressed={chartSource === 'snap'}
            onClick={() => onChartSourceChange?.('snap')}
            className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] ${
              chartSource === 'snap'
                ? 'border-zinc-900 bg-zinc-900 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-950'
            }`}
            disabled={!hasSnaps}
          >
            Saved Snap
          </button>
        </div>

        <div className="flex min-w-0 flex-1 flex-wrap items-center justify-start gap-3 lg:justify-end">
          <select
            aria-label="Directional saved snap"
            value={chartSource === 'snap' ? selectedSnapId : ''}
            onChange={(event) => onSnapChange?.(event.target.value)}
            disabled={loadingSnaps || !hasSnaps}
            className="h-8 min-w-[260px] max-w-full rounded-sm border border-zinc-200 bg-white px-3 text-[12px] text-zinc-700 outline-none focus:border-zinc-500 disabled:opacity-55"
          >
            <option value="">{snapMessage}</option>
            {snapOptions.map((snap) => (
              <option
                key={snap.id}
                value={snap.id}
                disabled={!isSavedSnapCalculationEligible(snap)}
              >
                {formatSnapLabel(snap)}
                {getSavedSnapIneligibilityLabel(snap)
                  ? ` — ${getSavedSnapIneligibilityLabel(snap)}`
                  : ''}
              </option>
            ))}
          </select>
          {typeof onRefreshSnaps === 'function' ? (
            <button
              type="button"
              onClick={() => onRefreshSnaps({ silent: true })}
              disabled={loadingSnaps}
              className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-zinc-600 hover:border-zinc-400 hover:text-zinc-950 disabled:opacity-55"
            >
              {loadingSnaps ? 'Loading' : 'Refresh'}
            </button>
          ) : null}
          {hasReviewRequiredSnaps ? (
            <span className="font-serif text-[11px] italic leading-5 text-zinc-500">
              Review-required and superseded saved charts are disabled. Use a corrected copy from Astro Clock.
            </span>
          ) : null}
          {chartSource === 'snap' && selectedSnap ? (
            <div className="min-w-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-zinc-500">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-600" />
              <span className="max-w-[240px] truncate font-medium text-zinc-800">{selectedParts.label}</span>
              {selectedParts.stamp ? <span className="text-zinc-300">/</span> : null}
              {selectedParts.stamp ? <span>{selectedParts.stamp}</span> : null}
              {selectedParts.location ? <span className="text-zinc-300">/</span> : null}
              {selectedParts.location ? <span className="max-w-[220px] truncate">{selectedParts.location}</span> : null}
              {selectedParts.timezone ? <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-zinc-400">{selectedParts.timezone}</span> : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function DirectionalStepButton({ label, ariaLabel, disabled, onClick }) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={onClick}
      className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-700 hover:border-zinc-400 hover:text-zinc-950 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {label}
    </button>
  );
}

export default function Directional3DModal({
  open,
  onClose,
  payload,
  loading,
  error,
  onRetry,
  chartSource = 'current',
  currentSourceLabel = 'Current',
  onChartSourceChange,
  snapOptions = [],
  selectedSnapId = '',
  selectedSnap = null,
  onSnapChange,
  loadingSnaps = false,
  snapsLoaded = true,
  onRefreshSnaps,
  onStepContext,
  canStepTime = true,
}) {
  const objects = useMemo(
    () => (Array.isArray(payload?.objects) ? payload.objects.filter(Boolean) : []),
    [payload],
  );
  const chartInfo = payload?.chart_info || {};
  const [system, setSystem] = useState('EQL');
  const [rotation, setRotation] = useState(9);
  const [tilt, setTilt] = useState(19);
  const [layers, setLayers] = useState(LAYER_PRESETS.EQL);
  const [selected, setSelected] = useState(null);
  const [sort, setSort] = useState({ key: 'name', direction: 'asc' });

  useEffect(() => {
    if (!payload) return;
    setRotation(toNumber(chartInfo.rotation, 9));
    setTilt(toNumber(chartInfo.tilt, 19));
    setSelected((Array.isArray(payload.objects) ? payload.objects.find(Boolean) : null) || null);
  }, [chartInfo.rotation, chartInfo.tilt, payload]);

  useEffect(() => {
    if (!open) setSelected(null);
  }, [open]);

  useEffect(() => {
    setLayers(LAYER_PRESETS[system] || LAYER_PRESETS.EQL);
  }, [system]);

  const sortedObjects = useMemo(() => {
    const rows = [...objects];
    const direction = sort.direction === 'asc' ? 1 : -1;
    rows.sort((left, right) => {
      const read = (row) => {
        if (sort.key === 'name') return String(row?.name || '');
        const [sortSystem, field] = sort.key.split('.');
        return toNumber(row?.[sortSystem]?.[field], Number.NEGATIVE_INFINITY);
      };
      const leftValue = read(left);
      const rightValue = read(right);
      if (typeof leftValue === 'string' || typeof rightValue === 'string') {
        return String(leftValue).localeCompare(String(rightValue)) * direction;
      }
      return (leftValue - rightValue) * direction;
    });
    return rows;
  }, [objects, sort]);

  if (!open) return null;

  const setSortKey = (key) => {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };
  const activeSystems = system === 'ALL' ? SYSTEMS : [system];
  const selectedObject = selected || null;
  const obliquity = toNumber(chartInfo.obliquity, 23.439291);
  const toggleLayer = (key) => {
    setLayers((current) => ({ ...current, [key]: !current[key] }));
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 p-4">
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-zinc-200 px-5 py-4">
          <div>
            <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-teal-700">
              Astro Clock / Directional
            </div>
            <h2 className="text-lg font-semibold text-zinc-950">Directional 3D</h2>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
              <span>UTC {chartInfo.utc_datetime || '--'}</span>
              <span>Lat {formatNumber(chartInfo.latitude, 4)}</span>
              <span>Lon {formatNumber(chartInfo.longitude, 4)}</span>
              <span>Houses {chartInfo.house_system || '--'}</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-zinc-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:bg-zinc-50"
          >
            Close
          </button>
        </div>
        <DirectionalSourceBar
          chartSource={chartSource}
          currentSourceLabel={currentSourceLabel}
          onChartSourceChange={onChartSourceChange}
          snapOptions={snapOptions}
          selectedSnapId={selectedSnapId}
          selectedSnap={selectedSnap}
          onSnapChange={onSnapChange}
          loadingSnaps={loadingSnaps}
          snapsLoaded={snapsLoaded}
          onRefreshSnaps={onRefreshSnaps}
        />

        <div className="overflow-y-auto p-5">
          {loading ? (
            <div className="flex min-h-[420px] items-center justify-center text-sm text-zinc-500">
              Loading Directional 3D...
            </div>
          ) : null}

          {!loading && error ? (
            <div className="flex min-h-[420px] flex-col items-center justify-center gap-3 text-center">
              <div className="text-sm font-medium text-red-600">{error}</div>
              {onRetry ? (
                <button
                  type="button"
                  onClick={onRetry}
                  className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-white"
                >
                  Retry
                </button>
              ) : null}
            </div>
          ) : null}

          {!loading && !error && objects.length === 0 ? (
            <div className="flex min-h-[420px] items-center justify-center text-sm text-zinc-500">
              No Directional objects returned for this chart.
            </div>
          ) : null}

          {!loading && !error && objects.length > 0 ? (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
              <div className="space-y-4">
                <div className="rounded-xl border border-zinc-200 bg-white p-3">
                  <DirectionalSphere
                    objects={objects}
                    system={system}
                    rotation={rotation}
                    tilt={tilt}
                    layers={layers}
                    obliquity={obliquity}
                    selectedId={selectedObject?.object_id}
                    onSelect={setSelected}
                  />
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
                    Rotation
                    <input
                      type="range"
                      min="0"
                      max="360"
                      step="1"
                      value={rotation}
                      onChange={(event) => setRotation(Number(event.target.value))}
                      className="mt-2 w-full accent-zinc-900"
                    />
                    <span className="mt-1 block text-xs normal-case tracking-normal text-zinc-700">
                      {formatNumber(rotation, 0)} deg
                    </span>
                  </label>
                  <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
                    Tilt
                    <input
                      type="range"
                      min="-90"
                      max="90"
                      step="1"
                      value={tilt}
                      onChange={(event) => setTilt(Number(event.target.value))}
                      className="mt-2 w-full accent-zinc-900"
                    />
                    <span className="mt-1 block text-xs normal-case tracking-normal text-zinc-700">
                      {formatNumber(tilt, 0)} deg
                    </span>
                  </label>
                </div>

                {typeof onStepContext === 'function' ? (
                  <div className="rounded-lg border border-zinc-200 p-3">
                    <div className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                      Step
                    </div>
                    <div className="grid gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="w-10 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400">Time</span>
                        <DirectionalStepButton
                          label="-1h"
                          ariaLabel="Time -1h"
                          disabled={loading || !canStepTime}
                          onClick={() => onStepContext({ hours: -1 })}
                        />
                        <DirectionalStepButton
                          label="+1h"
                          ariaLabel="Time +1h"
                          disabled={loading || !canStepTime}
                          onClick={() => onStepContext({ hours: 1 })}
                        />
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="w-10 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400">Lat</span>
                        <DirectionalStepButton
                          label="-1 deg"
                          ariaLabel="Latitude -1 deg"
                          disabled={loading}
                          onClick={() => onStepContext({ latitudeDelta: -1 })}
                        />
                        <DirectionalStepButton
                          label="+1 deg"
                          ariaLabel="Latitude +1 deg"
                          disabled={loading}
                          onClick={() => onStepContext({ latitudeDelta: 1 })}
                        />
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="w-10 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400">Lon</span>
                        <DirectionalStepButton
                          label="-1 deg"
                          ariaLabel="Longitude -1 deg"
                          disabled={loading}
                          onClick={() => onStepContext({ longitudeDelta: -1 })}
                        />
                        <DirectionalStepButton
                          label="+1 deg"
                          ariaLabel="Longitude +1 deg"
                          disabled={loading}
                          onClick={() => onStepContext({ longitudeDelta: 1 })}
                        />
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="rounded-lg border border-zinc-200 p-3">
                  <div className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                    Layers
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {LAYER_LABELS.map(([key, label]) => {
                      const active = Boolean(layers[key]);
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => toggleLayer(key)}
                          className={`rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${
                            active ? 'bg-zinc-900 text-white' : 'border border-zinc-200 text-zinc-600'
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="min-w-0 space-y-4">
                <div className="flex flex-wrap gap-2">
                  {[...SYSTEMS, 'ALL'].map((option) => (
                    <button
                      key={option}
                      type="button"
                      onClick={() => setSystem(option)}
                      className={`rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${
                        system === option ? 'bg-zinc-900 text-white' : 'border border-zinc-200 text-zinc-600'
                      }`}
                    >
                      {option === 'ALL' ? 'All systems' : option}
                    </button>
                  ))}
                </div>

                <div className="space-y-3">
                  <DirectionalInspector
                    activeSystems={activeSystems}
                    objectsCount={objects.length}
                    payloadSystems={payload?.systems}
                    selectedObject={selectedObject}
                  />

                  <div className="max-h-[360px] overflow-auto rounded-xl border border-zinc-200 bg-white">
                    <table className="min-w-full divide-y divide-zinc-100 text-left text-xs">
                      <thead className="sticky top-0 bg-zinc-50">
                        <tr>
                          <th className="px-3 py-2">
                            <SortButton
                              active={sort.key === 'name'}
                              direction={sort.direction}
                              onClick={() => setSortKey('name')}
                            >
                              Object
                            </SortButton>
                          </th>
                          {SYSTEMS.map((itemSystem) => (
                            <React.Fragment key={itemSystem}>
                              <th className="px-3 py-2">
                                <SortButton
                                  active={sort.key === `${itemSystem}.longitude`}
                                  direction={sort.direction}
                                  onClick={() => setSortKey(`${itemSystem}.longitude`)}
                                >
                                  {itemSystem} Lon
                                </SortButton>
                              </th>
                              <th className="px-3 py-2">
                                <SortButton
                                  active={sort.key === `${itemSystem}.latitude`}
                                  direction={sort.direction}
                                  onClick={() => setSortKey(`${itemSystem}.latitude`)}
                                >
                                  {itemSystem} Lat
                                </SortButton>
                              </th>
                            </React.Fragment>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 bg-white">
                        {sortedObjects.map((item) => {
                          const isCusp = isCuspObject(item);
                          return (
                            <tr
                              key={item.object_id}
                              className={selectedObject?.object_id === item.object_id ? 'bg-zinc-50' : ''}
                            >
                              <td className="whitespace-nowrap px-3 py-2">
                                <button
                                  type="button"
                                  onClick={() => setSelected(item)}
                                  className="flex items-center gap-2 text-left font-medium text-zinc-900"
                                >
                                  {!isCusp ? (
                                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-zinc-200 text-[13px]">
                                      {safeObjectSymbol(item)}
                                    </span>
                                  ) : null}
                                  <span>{item.name}</span>
                                </button>
                              </td>
                              {SYSTEMS.map((itemSystem) => (
                                <React.Fragment key={`${item.object_id}-${itemSystem}`}>
                                  <td className="whitespace-nowrap px-3 py-2 text-zinc-700">
                                    {formatNumber(item[itemSystem]?.longitude)}
                                  </td>
                                  <td className="whitespace-nowrap px-3 py-2 text-zinc-700">
                                    {item.bfull === false ? '' : formatNumber(item[itemSystem]?.latitude)}
                                  </td>
                                </React.Fragment>
                              ))}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
