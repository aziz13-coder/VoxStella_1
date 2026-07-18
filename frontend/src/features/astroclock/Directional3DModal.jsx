import React, {
  memo,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  formatSavedSnapDateTime,
  formatSavedSnapLabel,
  getSavedSnapIneligibilityLabel,
  isSavedSnapCalculationEligible,
} from './savedSnapViewModel.mjs';

const SYSTEMS = ['EQL', 'EQU', 'HOR'];
const EMPTY_OBJECTS = Object.freeze([]);
const DEFAULT_SYSTEM = 'HOR';
const DEFAULT_ROTATION = 0;
const DEFAULT_TILT = 19;
const SPHERE_SIZE = 320;
const SPHERE_CENTER = SPHERE_SIZE / 2;
const SPHERE_RADIUS_X = 126;
const SPHERE_RADIUS_Y = 118;
const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'select:not([disabled])',
  'input:not([disabled])',
  '[href]',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

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
    referenceKey: 'ecliptic',
    referenceLabel: 'Ecliptic',
  },
  EQU: {
    label: 'EQU',
    name: 'Equatorial',
    longitudeLabel: 'RA',
    latitudeLabel: 'Dec',
    referenceKey: 'equator',
    referenceLabel: 'Equator',
  },
  HOR: {
    label: 'HOR',
    name: 'Horizon',
    longitudeLabel: 'Az',
    latitudeLabel: 'Alt',
    referenceKey: 'horizon',
    referenceLabel: 'Horizon',
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
  EQL: {
    objects: true,
    ecliptic: true,
    equator: false,
    horizon: false,
    tropics: false,
    polarCircles: false,
    axes: true,
    houses: true,
    backPoints: true,
  },
  EQU: {
    objects: true,
    ecliptic: false,
    equator: true,
    horizon: false,
    tropics: true,
    polarCircles: true,
    axes: true,
    houses: false,
    backPoints: true,
  },
  HOR: {
    objects: true,
    ecliptic: false,
    equator: false,
    horizon: true,
    tropics: false,
    polarCircles: false,
    axes: true,
    houses: false,
    backPoints: true,
  },
  ALL: {
    objects: true,
    ecliptic: true,
    equator: true,
    horizon: true,
    tropics: true,
    polarCircles: true,
    axes: true,
    houses: true,
    backPoints: true,
  },
};

const LAYER_DETAILS = {
  objects: 'Objects',
  ecliptic: 'Ecliptic',
  equator: 'Equator',
  horizon: 'Horizon',
  tropics: 'Tropics',
  polarCircles: 'Polar',
  axes: 'Axes',
  houses: 'Cusp points',
  backPoints: 'Back points',
};

const RELEVANT_LAYERS = {
  EQL: ['objects', 'ecliptic', 'axes', 'houses', 'backPoints'],
  EQU: ['objects', 'equator', 'tropics', 'polarCircles', 'axes', 'backPoints'],
  HOR: ['objects', 'horizon', 'axes', 'backPoints'],
  ALL: [
    'objects',
    'ecliptic',
    'equator',
    'horizon',
    'tropics',
    'polarCircles',
    'axes',
    'houses',
    'backPoints',
  ],
};

function asFiniteNumber(value) {
  if (value === null || value === undefined || typeof value === 'boolean') return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function numberOr(value, fallback) {
  return asFiniteNumber(value) ?? fallback;
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function toRadians(degrees) {
  return (degrees * Math.PI) / 180;
}

function normalizeDegrees(degrees) {
  const number = asFiniteNumber(degrees);
  if (number === null) return null;
  const wrapped = number % 360;
  return wrapped < 0 ? wrapped + 360 : wrapped;
}

function formatNumber(value, digits = 2) {
  const number = asFiniteNumber(value);
  return number === null ? 'Unavailable' : number.toFixed(digits);
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
  return {
    label: String(firstPresent(snap?.label, snap?.id, 'Untitled snap') || 'Untitled snap').trim(),
    stamp: formatSavedSnapDateTime(snap),
    location: String(firstPresent(snap?.location, dashboard?.location, '') || '').trim(),
    timezone: String(
      firstPresent(
        snap?.timezone,
        dashboard?.timezone,
        snap?.timezone_label,
        dashboard?.timezone_label,
        '',
      ) || '',
    ).trim(),
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
  if (symbol && !symbol.includes('\uFFFD') && !/[ÃÂ]/.test(symbol)) return symbol;
  return String(item.name || '?').slice(0, 2).trim() || '?';
}

function isCuspObject(item) {
  return item?.object_type === 'cusp' || item?.bfull === false;
}

function objectAccentColor(item, fallback) {
  return OBJECT_COLORS[item?.name] || fallback || '#111827';
}

function validCoordinate(coord) {
  const longitude = asFiniteNumber(coord?.longitude);
  const latitude = asFiniteNumber(coord?.latitude);
  return longitude !== null
    && latitude !== null
    && latitude >= -90
    && latitude <= 90;
}

function friendlySource(value) {
  const text = String(value || '').trim();
  if (!text) return 'Source unavailable';
  return text
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function sourceMarksUnavailable(value) {
  return ['unavailable', 'static_zero', 'not_applicable'].includes(
    String(value || '').trim().toLowerCase(),
  );
}

function objectIdentity(item) {
  return String(item?.object_id || '').trim();
}

function isValidObject(item) {
  return Boolean(
    item
    && typeof item === 'object'
    && objectIdentity(item)
    && String(item.name || '').trim()
    && SYSTEMS.some((system) => validCoordinate(item?.[system])),
  );
}

function payloadVector(vector) {
  const sourceX = asFiniteNumber(vector?.x);
  const sourceY = asFiniteNumber(vector?.y);
  const sourceZ = asFiniteNumber(vector?.z);
  if (sourceX === null || sourceY === null || sourceZ === null) return null;
  const magnitude = Math.hypot(sourceX, sourceY, sourceZ);
  if (magnitude <= 0) return null;
  return {
    x: sourceY / magnitude,
    y: sourceZ / magnitude,
    z: sourceX / magnitude,
  };
}

function coordinateVector(coord, vector) {
  const supplied = payloadVector(vector);
  if (supplied) return supplied;
  if (!validCoordinate(coord)) return null;
  const longitude = toRadians(normalizeDegrees(coord.longitude));
  const latitude = toRadians(asFiniteNumber(coord.latitude));
  const cosLatitude = Math.cos(latitude);
  return {
    x: cosLatitude * Math.sin(longitude),
    y: Math.sin(latitude),
    z: cosLatitude * Math.cos(longitude),
  };
}

/**
 * Orthographic projection for one coordinate frame.
 *
 * Every pane is projected independently in its own native frame. The x screen
 * axis, y screen axis, and camera depth are deliberately separate values.
 */
export function projectDirectionalCoordinate(
  coord,
  rotation = DEFAULT_ROTATION,
  tilt = DEFAULT_TILT,
  radiusX = SPHERE_RADIUS_X,
  radiusY = SPHERE_RADIUS_Y,
  center = SPHERE_CENTER,
  vector = null,
) {
  const coordinate = coordinateVector(coord, vector);
  if (!coordinate) return null;

  const yaw = toRadians(numberOr(rotation, DEFAULT_ROTATION));
  const pitch = toRadians(numberOr(tilt, DEFAULT_TILT));

  const yawX = (coordinate.x * Math.cos(yaw)) - (coordinate.z * Math.sin(yaw));
  const yawZ = (coordinate.x * Math.sin(yaw)) + (coordinate.z * Math.cos(yaw));
  const viewY = (coordinate.y * Math.cos(pitch)) - (yawZ * Math.sin(pitch));
  const depth = (coordinate.y * Math.sin(pitch)) + (yawZ * Math.cos(pitch));

  return {
    x: center + (radiusX * yawX),
    y: center - (radiusY * viewY),
    depth,
    hidden: depth < 0,
  };
}

function circleCoordinates(kind, latitude = 0) {
  const coordinates = [];
  for (let step = 0; step <= 360; step += 6) {
    coordinates.push(
      kind === 'vertical'
        ? {
          longitude: step <= 180 ? 0 : 180,
          latitude: step <= 180 ? step - 90 : 270 - step,
        }
        : { longitude: step, latitude },
    );
  }
  return coordinates;
}

function projectedSegments(coordinates, rotation, tilt) {
  const segments = [];
  let current = null;
  let previous = null;

  for (const coordinate of coordinates) {
    const point = projectDirectionalCoordinate(coordinate, rotation, tilt);
    if (!point) continue;

    if (!current || current.hidden !== point.hidden) {
      if (current && current.points.length > 1) segments.push(current);
      current = {
        hidden: point.hidden,
        points: previous ? [previous, point] : [point],
      };
    } else {
      current.points.push(point);
    }
    previous = point;
  }

  if (current && current.points.length > 1) segments.push(current);
  return segments.map((segment, index) => ({
    ...segment,
    key: `${segment.hidden ? 'back' : 'front'}-${index}`,
    path: segment.points
      .map((point, pointIndex) => `${pointIndex === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
      .join(' '),
  }));
}

function resolveLabelCollisions(rows) {
  const occupied = [];
  const offsets = [
    [0, 0],
    [14, 0],
    [-14, 0],
    [0, 14],
    [0, -14],
    [11, 11],
    [-11, 11],
    [11, -11],
    [-11, -11],
    [22, 0],
    [-22, 0],
  ];

  return rows.map((row) => {
    const chosen = offsets.find(([offsetX, offsetY]) => occupied.every((position) => {
      const deltaX = (row.point.x + offsetX) - position.x;
      const deltaY = (row.point.y + offsetY) - position.y;
      return Math.hypot(deltaX, deltaY) >= 18;
    })) || offsets[offsets.length - 1];

    const displayPoint = {
      x: row.point.x + chosen[0],
      y: row.point.y + chosen[1],
    };
    occupied.push(displayPoint);
    return {
      ...row,
      displayPoint,
      displaced: chosen[0] !== 0 || chosen[1] !== 0,
    };
  });
}

function CoordinateReadout({ label, value, unavailable = false }) {
  const displayValue = unavailable ? 'Unavailable' : formatNumber(value);
  return (
    <div className="min-w-0">
      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400">
        {label}
      </div>
      <div
        className={`mt-1 break-words text-sm font-semibold tabular-nums ${
          displayValue === 'Unavailable' ? 'text-zinc-400' : 'text-zinc-950'
        }`}
      >
        {displayValue}
      </div>
    </div>
  );
}

function CoordinateSystemPanel({ item, system, selectedSystem }) {
  const details = SYSTEM_DETAILS[system] || SYSTEM_DETAILS.EQL;
  const coord = item?.[system];
  const meta = item?.coordinate_meta?.[system] || {};
  const cusp = isCuspObject(item);
  const hasLatitude = item?.bfull !== false && asFiniteNumber(coord?.latitude) !== null;
  const speedUnavailable = sourceMarksUnavailable(meta.speed_source)
    || asFiniteNumber(coord?.speed) === null;
  const latitudeSpeedUnavailable = sourceMarksUnavailable(meta.latitude_speed_source)
    || asFiniteNumber(coord?.latitude_speed) === null;
  const active = selectedSystem === system;

  return (
    <div
      data-directional-coordinate-panel={system}
      className={`min-w-0 p-3 sm:p-4 ${active ? 'bg-zinc-50' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-400">
            {details.label}
          </div>
          <div className="mt-1 truncate text-sm font-semibold text-zinc-950">
            {details.name}{active ? ' · Selected frame' : ''}
          </div>
        </div>
        <span
          aria-hidden="true"
          className="mt-1 h-2 w-2 flex-none rounded-full"
          style={{ backgroundColor: SYSTEM_COLORS[system] }}
        />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <CoordinateReadout label={details.longitudeLabel} value={coord?.longitude} />
        <CoordinateReadout
          label={details.latitudeLabel}
          value={coord?.latitude}
          unavailable={!hasLatitude}
        />
      </div>

      {cusp ? (
        <div className="mt-3 border-t border-zinc-100 pt-3 text-[11px] text-zinc-500">
          Motion is not provided for cusp points.
        </div>
      ) : (
        <div className="mt-3 space-y-2 border-t border-zinc-100 pt-3 text-[11px] text-zinc-500">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium text-zinc-700">
              Speed {speedUnavailable ? 'Unavailable' : formatNumber(coord?.speed, 3)}
            </span>
            {!speedUnavailable ? <span className="text-zinc-400">deg/day</span> : null}
          </div>
          {(system === 'EQU' || system === 'HOR') ? (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-zinc-700">
                Lat speed {latitudeSpeedUnavailable
                  ? 'Unavailable'
                  : formatNumber(coord?.latitude_speed, 3)}
              </span>
              {!latitudeSpeedUnavailable ? <span className="text-zinc-400">deg/day</span> : null}
            </div>
          ) : null}
        </div>
      )}

      <div className="mt-3 space-y-1 border-t border-zinc-100 pt-3 text-[10px] leading-4 text-zinc-400">
        <div>Position: {friendlySource(meta.source)}</div>
        {!cusp ? <div>Motion: {friendlySource(meta.speed_source)}</div> : null}
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

function DirectionalInspector({
  activeSystems,
  objectsCount,
  payloadSystems,
  selectedObject,
  selectedSystem,
}) {
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
        <InspectorMetric label="Rows">
          <span className="tabular-nums">{objectsCount}</span>
        </InspectorMetric>
        <InspectorMetric label="Selected object">
          {selectedObject ? (
            <span className="flex min-w-0 items-center gap-2">
              {!selectedIsCusp ? (
                <span
                  aria-hidden="true"
                  className="text-lg leading-none"
                  style={{ color: selectedAccent }}
                >
                  {safeObjectSymbol(selectedObject)}
                </span>
              ) : null}
              <span className="truncate">
                {selectedObject.name} · {SYSTEM_DETAILS[selectedSystem]?.label || selectedSystem}
              </span>
            </span>
          ) : (
            'None'
          )}
        </InspectorMetric>
        <InspectorMetric label="Available systems">
          <span className="truncate">{systemsLabel}</span>
        </InspectorMetric>
      </div>

      {selectedObject ? (
        <div className="grid divide-y divide-zinc-100 border-t border-zinc-100 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          {SYSTEMS.map((itemSystem) => (
            <CoordinateSystemPanel
              key={itemSystem}
              item={selectedObject}
              system={itemSystem}
              selectedSystem={selectedSystem}
            />
          ))}
        </div>
      ) : (
        <div className="border-t border-zinc-100 p-4 text-sm text-zinc-500">
          Select an available coordinate in the table to inspect it.
        </div>
      )}
    </section>
  );
}

function SortHeader({ activeKey, direction, label, sortKey, onSort }) {
  const active = activeKey === sortKey;
  return (
    <th
      scope="col"
      aria-sort={active ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'}
      className="px-3 py-2"
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`rounded-sm text-left text-[10px] font-semibold uppercase tracking-[0.12em] outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 ${
          active ? 'text-zinc-950' : 'text-zinc-500'
        }`}
      >
        {label}{active ? (direction === 'asc' ? ' \u2191' : ' \u2193') : ''}
      </button>
    </th>
  );
}

function SegmentedCircle({
  coordinates,
  rotation,
  tilt,
  stroke,
  dash,
  frontOpacity = 0.72,
  backOpacity = 0.13,
  width = 1.1,
  dataAttribute,
}) {
  const segments = useMemo(
    () => projectedSegments(coordinates, rotation, tilt),
    [coordinates, rotation, tilt],
  );
  return segments.map((segment) => (
    <path
      key={segment.key}
      {...dataAttribute}
      d={segment.path}
      fill="none"
      stroke={stroke}
      strokeDasharray={segment.hidden ? '2 5' : dash}
      strokeWidth={width}
      opacity={segment.hidden ? backOpacity : frontOpacity}
    />
  ));
}

const DirectionalSphere = memo(function DirectionalSphere({
  objects,
  system,
  rotation,
  tilt,
  layers,
  selectedObjectId,
  selectedSystem,
}) {
  const details = SYSTEM_DETAILS[system];
  const objectRows = useMemo(() => {
    const rows = objects.flatMap((item) => {
      if (isCuspObject(item) || !validCoordinate(item?.[system])) return [];
      const point = projectDirectionalCoordinate(
        item[system],
        rotation,
        tilt,
        SPHERE_RADIUS_X,
        SPHERE_RADIUS_Y,
        SPHERE_CENTER,
        item?.vectors?.[system],
      );
      return point ? [{ item, point }] : [];
    });
    rows.sort((left, right) => left.point.depth - right.point.depth);
    return resolveLabelCollisions(
      layers.backPoints ? rows : rows.filter((row) => !row.point.hidden),
    );
  }, [layers.backPoints, objects, rotation, system, tilt]);

  const cuspRows = useMemo(() => {
    if (system !== 'EQL') return [];
    return objects.flatMap((item) => {
      if (!isCuspObject(item) || !validCoordinate(item?.EQL)) return [];
      const point = projectDirectionalCoordinate(
        item.EQL,
        rotation,
        tilt,
        SPHERE_RADIUS_X,
        SPHERE_RADIUS_Y,
        SPHERE_CENTER,
        item?.vectors?.EQL,
      );
      return point ? [{ item, point }] : [];
    });
  }, [objects, rotation, system, tilt]);

  const horizontalCoordinates = useMemo(() => circleCoordinates('horizontal'), []);
  const verticalCoordinates = useMemo(() => circleCoordinates('vertical'), []);
  const tropicNorth = useMemo(() => circleCoordinates('horizontal', 23.439291), []);
  const tropicSouth = useMemo(() => circleCoordinates('horizontal', -23.439291), []);
  const polarNorth = useMemo(() => circleCoordinates('horizontal', 66.560709), []);
  const polarSouth = useMemo(() => circleCoordinates('horizontal', -66.560709), []);
  const referenceVisible = Boolean(layers[details.referenceKey]);
  const sphereLabel = `${details.name} Directional 3D chart`;

  return (
    <svg
      viewBox={`0 0 ${SPHERE_SIZE} ${SPHERE_SIZE}`}
      className="h-auto w-full select-none"
      role="img"
      aria-label={sphereLabel}
      shapeRendering="geometricPrecision"
      textRendering="optimizeLegibility"
    >
      <defs>
        <filter id={`directional-selected-glow-${system}`} x="-90%" y="-90%" width="280%" height="280%">
          <feDropShadow dx="0" dy="0" stdDeviation="2.2" floodColor="currentColor" floodOpacity="0.82" />
          <feDropShadow dx="0" dy="0" stdDeviation="5.8" floodColor="currentColor" floodOpacity="0.36" />
        </filter>
      </defs>
      <ellipse
        cx={SPHERE_CENTER}
        cy={SPHERE_CENTER}
        rx={SPHERE_RADIUS_X}
        ry={SPHERE_RADIUS_Y}
        fill="#fafafa"
        stroke="#d4d4d8"
        strokeWidth="1.5"
      />

      {referenceVisible ? (
        <SegmentedCircle
          coordinates={horizontalCoordinates}
          rotation={rotation}
          tilt={tilt}
          stroke={SYSTEM_COLORS[system]}
          dash={system === 'EQL' ? '' : system === 'EQU' ? '5 4' : '2 4'}
          dataAttribute={{ 'data-directional-reference-plane': system }}
        />
      ) : null}

      {layers.axes ? (
        <SegmentedCircle
          coordinates={verticalCoordinates}
          rotation={rotation}
          tilt={tilt}
          stroke={SYSTEM_COLORS[system]}
          dash="4 6"
          frontOpacity={0.44}
          backOpacity={0.09}
          width={0.9}
          dataAttribute={{ 'data-directional-axis': system }}
        />
      ) : null}

      {system === 'EQU' && layers.tropics ? (
        <>
          <SegmentedCircle
            coordinates={tropicNorth}
            rotation={rotation}
            tilt={tilt}
            stroke="#14b8a6"
            dash="6 5"
            frontOpacity={0.45}
            backOpacity={0.09}
            width={0.9}
            dataAttribute={{ 'data-directional-reference': 'tropic' }}
          />
          <SegmentedCircle
            coordinates={tropicSouth}
            rotation={rotation}
            tilt={tilt}
            stroke="#14b8a6"
            dash="6 5"
            frontOpacity={0.45}
            backOpacity={0.09}
            width={0.9}
            dataAttribute={{ 'data-directional-reference': 'tropic' }}
          />
        </>
      ) : null}

      {system === 'EQU' && layers.polarCircles ? (
        <>
          <SegmentedCircle
            coordinates={polarNorth}
            rotation={rotation}
            tilt={tilt}
            stroke="#71717a"
            dash="2 5"
            frontOpacity={0.36}
            backOpacity={0.07}
            width={0.9}
            dataAttribute={{ 'data-directional-reference': 'polar' }}
          />
          <SegmentedCircle
            coordinates={polarSouth}
            rotation={rotation}
            tilt={tilt}
            stroke="#71717a"
            dash="2 5"
            frontOpacity={0.36}
            backOpacity={0.07}
            width={0.9}
            dataAttribute={{ 'data-directional-reference': 'polar' }}
          />
        </>
      ) : null}

      {layers.houses ? cuspRows.map(({ item, point }) => {
        if (point.hidden && !layers.backPoints) return null;
        const selected = selectedObjectId === objectIdentity(item) && selectedSystem === system;
        return (
          <g
            key={`cusp-${objectIdentity(item)}`}
            data-directional-house-cusp={objectIdentity(item)}
            opacity={point.hidden ? 0.3 : 0.82}
            aria-hidden="true"
          >
            <circle
              cx={point.x}
              cy={point.y}
              r={selected ? 4.5 : 3}
              fill={selected ? '#18181b' : '#71717a'}
              stroke="#fff"
              strokeWidth="1.5"
            />
            <text
              x={point.x}
              y={point.y - 7}
              textAnchor="middle"
              fontSize="8"
              fontWeight="700"
              fill="#52525b"
              paintOrder="stroke"
              stroke="#fff"
              strokeWidth="3"
            >
              {safeObjectSymbol(item)}
            </text>
          </g>
        );
      }) : null}

      {layers.objects ? objectRows.map(({
        item,
        point,
        displayPoint,
        displaced,
      }) => {
        if (point.hidden && !layers.backPoints) return null;
        const selected = selectedObjectId === objectIdentity(item) && selectedSystem === system;
        const baseColor = SYSTEM_COLORS[system];
        const accent = selected ? objectAccentColor(item, baseColor) : baseColor;
        return (
          <g
            key={`${system}-${objectIdentity(item)}`}
            data-directional-object={objectIdentity(item)}
            data-directional-depth={point.depth.toFixed(6)}
            data-directional-side={point.hidden ? 'back' : 'front'}
            opacity={point.hidden ? 0.34 : 1}
            aria-hidden="true"
          >
            {displaced ? (
              <line
                x1={point.x}
                y1={point.y}
                x2={displayPoint.x}
                y2={displayPoint.y}
                stroke={accent}
                strokeWidth="0.75"
                opacity="0.4"
              />
            ) : null}
            <text
              data-directional-selected-object={selected ? objectIdentity(item) : undefined}
              data-directional-selected-system={selected ? system : undefined}
              x={displayPoint.x}
              y={displayPoint.y + 0.5}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={selected ? '18' : '15'}
              fontWeight={selected ? '800' : '700'}
              fill={accent}
              color={accent}
              filter={selected ? `url(#directional-selected-glow-${system})` : undefined}
              paintOrder={selected ? undefined : 'stroke'}
              stroke={selected ? 'none' : '#fff'}
              strokeWidth={selected ? '0' : '3.4'}
              strokeLinejoin="round"
              style={{ fontFamily: 'Georgia, Cambria, Times New Roman, serif' }}
            >
              {safeObjectSymbol(item)}
            </text>
          </g>
        );
      }) : null}
    </svg>
  );
});

function SpherePane({
  objects,
  system,
  rotation,
  tilt,
  layers,
  selectedObjectId,
  selectedSystem,
  onPointerDown,
  onPointerMove,
  onPointerUp,
}) {
  const details = SYSTEM_DETAILS[system];
  return (
    <section
      className="min-w-0 rounded-xl border border-zinc-200 bg-white p-2 sm:p-3"
      aria-labelledby={`directional-pane-${system}`}
    >
      <div className="mb-1 flex items-center justify-between gap-2 px-1">
        <div className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden="true"
            className="h-2 w-2 flex-none rounded-full"
            style={{ backgroundColor: SYSTEM_COLORS[system] }}
          />
          <h3 id={`directional-pane-${system}`} className="truncate text-xs font-semibold text-zinc-900">
            {details.name} ({system})
          </h3>
        </div>
        <span className="text-[10px] text-zinc-400">
          {details.longitudeLabel} / {details.latitudeLabel}
        </span>
      </div>
      <div
        data-directional-orbit-surface={system}
        className="cursor-grab touch-none rounded-lg outline-none active:cursor-grabbing"
        style={{ touchAction: 'none' }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <DirectionalSphere
          objects={objects}
          system={system}
          rotation={rotation}
          tilt={tilt}
          layers={layers}
          selectedObjectId={selectedObjectId}
          selectedSystem={selectedSystem}
        />
      </div>
      <p className="px-1 pb-1 text-center text-[9px] leading-4 text-zinc-400">
        {system === 'HOR'
          ? 'N 0° · E 90° · S 180° · W 270°'
          : 'Longitude increases 0° → 90° → 180° → 270°'}
      </p>
    </section>
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
  const allSnapOptions = Array.isArray(snapOptions) ? snapOptions : [];
  const eligibleSnapOptions = allSnapOptions.filter(isSavedSnapCalculationEligible);
  const hasSnaps = eligibleSnapOptions.length > 0;
  const hasReviewRequiredSnaps = allSnapOptions.some((snap) => !isSavedSnapCalculationEligible(snap));
  const selectedParts = getSnapParts(selectedSnap);
  const snapMessage = loadingSnaps
    ? 'Loading saved snaps...'
    : !snapsLoaded
      ? 'Refresh saved snaps'
      : !hasSnaps
        ? 'No saved snaps'
        : 'Select a saved snap';

  return (
    <div className="border-b border-zinc-200 bg-white px-3 py-3 sm:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
            Chart Source
          </span>
          <button
            type="button"
            aria-pressed={chartSource === 'current'}
            onClick={() => onChartSourceChange?.('current')}
            className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 ${
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
            disabled={!hasSnaps}
            className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
              chartSource === 'snap'
                ? 'border-zinc-900 bg-zinc-900 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-950'
            }`}
          >
            Saved Snap
          </button>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center lg:justify-end">
          <select
            aria-label="Directional saved snap"
            value={chartSource === 'snap' ? selectedSnapId : ''}
            onChange={(event) => onSnapChange?.(event.target.value)}
            disabled={loadingSnaps || !hasSnaps}
            className="h-9 w-full min-w-0 rounded-sm border border-zinc-200 bg-white px-3 text-[12px] text-zinc-700 outline-none focus:border-zinc-500 focus-visible:ring-2 focus-visible:ring-teal-600 sm:w-auto sm:min-w-[240px] disabled:opacity-55"
          >
            <option value="">{snapMessage}</option>
            {allSnapOptions.map((snap) => (
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
              className="self-start rounded-full border border-zinc-200 bg-white px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-zinc-600 outline-none hover:border-zinc-400 hover:text-zinc-950 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 disabled:opacity-55"
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
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-zinc-500">
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-teal-600" />
              <span className="max-w-[240px] truncate font-medium text-zinc-800">{selectedParts.label}</span>
              {selectedParts.stamp ? <span className="text-zinc-300">/</span> : null}
              {selectedParts.stamp ? <span>{selectedParts.stamp}</span> : null}
              {selectedParts.location ? <span className="text-zinc-300">/</span> : null}
              {selectedParts.location ? <span className="max-w-[220px] truncate">{selectedParts.location}</span> : null}
              {selectedParts.timezone ? (
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-zinc-400">
                  {selectedParts.timezone}
                </span>
              ) : null}
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
      className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-700 outline-none hover:border-zinc-400 hover:text-zinc-950 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {label}
    </button>
  );
}

function compareRows(left, right, sort) {
  if (sort.key === 'name') {
    const comparison = String(left?.name || '').localeCompare(String(right?.name || ''));
    return comparison * (sort.direction === 'asc' ? 1 : -1);
  }

  const [system, field] = sort.key.split('.');
  const leftValue = asFiniteNumber(left?.[system]?.[field]);
  const rightValue = asFiniteNumber(right?.[system]?.[field]);
  if (leftValue === null && rightValue === null) return 0;
  if (leftValue === null) return 1;
  if (rightValue === null) return -1;
  return (leftValue - rightValue) * (sort.direction === 'asc' ? 1 : -1);
}

function formatGap(gap) {
  if (typeof gap === 'string') return gap;
  if (gap && typeof gap === 'object') {
    return String(firstPresent(gap.message, gap.reason, gap.code, JSON.stringify(gap)));
  }
  return String(gap || '');
}

function bodyScopeLabel(scope) {
  if (scope === 'traditional_plus_modern') return 'Traditional + modern';
  if (scope === 'traditional') return 'Traditional';
  return scope ? friendlySource(scope) : 'Policy unavailable';
}

function DirectionalModelContext({ bodyPolicy, chartInfo, frameContext }) {
  const includedBodies = Array.isArray(bodyPolicy?.included) ? bodyPolicy.included : [];
  const excludedPoints = Array.isArray(bodyPolicy?.excluded_points) ? bodyPolicy.excluded_points : [];
  const requestedHouseSystem = String(chartInfo.house_system_requested || '').trim();
  const effectiveHouseSystem = String(
    chartInfo.house_system_effective || chartInfo.house_system || '',
  ).trim();
  const houseAdjusted = Boolean(chartInfo.house_system_adjusted)
    || Boolean(
      requestedHouseSystem
      && effectiveHouseSystem
      && requestedHouseSystem.toUpperCase() !== effectiveHouseSystem.toUpperCase(),
    );
  const lst = asFiniteNumber(frameContext?.local_sidereal_time_deg);

  return (
    <aside
      aria-label="Directional model context"
      className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-[11px] leading-5 text-zinc-600"
    >
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <span>
          <strong className="font-semibold text-zinc-800">Bodies:</strong>{' '}
          {bodyScopeLabel(bodyPolicy?.scope)}
          {includedBodies.length ? ` (${includedBodies.length})` : ''}
        </span>
        <span>
          <strong className="font-semibold text-zinc-800">EQL:</strong>{' '}
          {friendlySource(frameContext?.ecliptic_frame)}
        </span>
        <span>
          <strong className="font-semibold text-zinc-800">EQU:</strong>{' '}
          {friendlySource(frameContext?.equatorial_frame)}
        </span>
        <span>
          <strong className="font-semibold text-zinc-800">HOR:</strong>{' '}
          {friendlySource(frameContext?.horizon_frame || frameContext?.observer_frame)}
        </span>
        <span>
          <strong className="font-semibold text-zinc-800">Azimuth:</strong>{' '}
          N 0° · E 90°
        </span>
        {lst !== null ? (
          <span>
            <strong className="font-semibold text-zinc-800">LST:</strong>{' '}
            {formatNumber(lst)}°
          </span>
        ) : null}
        {effectiveHouseSystem ? (
          <span>
            <strong className="font-semibold text-zinc-800">Houses:</strong>{' '}
            {effectiveHouseSystem}
            {houseAdjusted && requestedHouseSystem
              ? ` (requested ${requestedHouseSystem})`
              : ''}
          </span>
        ) : null}
      </div>
      {excludedPoints.length ? (
        <div className="mt-1 text-zinc-500">
          Points outside this body set: {excludedPoints.join(', ')}.
        </div>
      ) : null}
      {chartInfo.polar_region ? (
        <div className="mt-1 font-medium text-amber-800">
          Polar latitude: cusp availability follows the effective house system returned with this chart.
        </div>
      ) : null}
    </aside>
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
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);
  const previousFocusRef = useRef(null);
  const wasOpenRef = useRef(false);
  const cameraInitializedForOpenRef = useRef(false);
  const onCloseRef = useRef(onClose);
  const dragRef = useRef(null);
  onCloseRef.current = onClose;

  const sourceObjects = Array.isArray(payload?.objects) ? payload.objects : EMPTY_OBJECTS;
  const objects = useMemo(() => sourceObjects.filter(isValidObject), [sourceObjects]);
  const invalidObjectCount = sourceObjects.length - objects.length;
  const chartInfo = payload?.chart_info && typeof payload.chart_info === 'object'
    ? payload.chart_info
    : {};
  const bodyPolicy = payload?.body_policy && typeof payload.body_policy === 'object'
    ? payload.body_policy
    : {};
  const frameContext = payload?.frame_context && typeof payload.frame_context === 'object'
    ? payload.frame_context
    : {};
  const dataGaps = Array.isArray(chartInfo.data_gaps)
    ? chartInfo.data_gaps.map(formatGap).filter(Boolean)
    : [];

  const [system, setSystem] = useState(DEFAULT_SYSTEM);
  const [rotation, setRotation] = useState(DEFAULT_ROTATION);
  const [tilt, setTilt] = useState(DEFAULT_TILT);
  const [layers, setLayers] = useState(LAYER_PRESETS[DEFAULT_SYSTEM]);
  const [selection, setSelection] = useState({ objectId: '', system: DEFAULT_SYSTEM });
  const [sort, setSort] = useState({ key: 'name', direction: 'asc' });

  useEffect(() => {
    if (open && !wasOpenRef.current) {
      cameraInitializedForOpenRef.current = false;
      setSystem(DEFAULT_SYSTEM);
      setLayers(LAYER_PRESETS[DEFAULT_SYSTEM]);
      setRotation(DEFAULT_ROTATION);
      setTilt(DEFAULT_TILT);
      setSelection((current) => ({ ...current, system: DEFAULT_SYSTEM }));
    } else if (!open) {
      cameraInitializedForOpenRef.current = false;
    }
    wasOpenRef.current = open;
  }, [open]);

  useEffect(() => {
    if (
      !open
      || cameraInitializedForOpenRef.current
      || !payload
      || typeof payload !== 'object'
    ) return;
    const hasCameraMetadata = asFiniteNumber(chartInfo.rotation) !== null
      || asFiniteNumber(chartInfo.tilt) !== null;
    if (!hasCameraMetadata && !Array.isArray(payload.objects)) return;
    setRotation(numberOr(chartInfo.rotation, DEFAULT_ROTATION));
    setTilt(clamp(numberOr(chartInfo.tilt, DEFAULT_TILT), -90, 90));
    cameraInitializedForOpenRef.current = true;
  }, [chartInfo.rotation, chartInfo.tilt, open, payload]);

  useEffect(() => {
    if (!open) return;
    setSelection((current) => {
      const requestedSystems = system === 'ALL'
        ? [
          ...(SYSTEMS.includes(current.system) ? [current.system] : []),
          ...SYSTEMS.filter((itemSystem) => itemSystem !== current.system),
        ]
        : [system];

      for (const itemSystem of requestedSystems) {
        const currentObject = objects.find(
          (item) => objectIdentity(item) === current.objectId
            && validCoordinate(item?.[itemSystem]),
        );
        if (currentObject) {
          if (current.system === itemSystem) return current;
          return { objectId: current.objectId, system: itemSystem };
        }

        const preferred = objects.find(
          (item) => !isCuspObject(item) && validCoordinate(item?.[itemSystem]),
        ) || objects.find((item) => validCoordinate(item?.[itemSystem]));
        if (preferred) {
          return { objectId: objectIdentity(preferred), system: itemSystem };
        }
      }

      const emptySelection = {
        objectId: '',
        system: system === 'ALL' ? DEFAULT_SYSTEM : system,
      };
      return current.objectId === emptySelection.objectId
        && current.system === emptySelection.system
        ? current
        : emptySelection;
    });
  }, [objects, open, system]);

  useEffect(() => {
    if (!open || typeof document === 'undefined') return undefined;
    previousFocusRef.current = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusTimer = window.setTimeout(() => closeButtonRef.current?.focus(), 0);

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        onCloseRef.current?.();
        return;
      }
      if (event.key !== 'Tab') return;
      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(dialog.querySelectorAll(FOCUSABLE_SELECTOR))
        .filter((element) => !element.disabled && element.getAttribute('aria-hidden') !== 'true');
      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      } else if (!dialog.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      const previousFocus = previousFocusRef.current;
      if (previousFocus && typeof previousFocus.focus === 'function' && document.contains(previousFocus)) {
        previousFocus.focus();
      }
    };
  }, [open]);

  const sortedObjects = useMemo(
    () => [...objects].sort((left, right) => compareRows(left, right, sort)),
    [objects, sort],
  );
  const selectedObject = useMemo(
    () => objects.find((item) => objectIdentity(item) === selection.objectId) || null,
    [objects, selection.objectId],
  );
  const activeSystems = system === 'ALL' ? SYSTEMS : [system];
  const relevantLayers = RELEVANT_LAYERS[system] || RELEVANT_LAYERS[DEFAULT_SYSTEM];

  const selectSystem = useCallback((nextSystem) => {
    setSystem(nextSystem);
    setLayers(LAYER_PRESETS[nextSystem] || LAYER_PRESETS[DEFAULT_SYSTEM]);
  }, []);

  const selectObject = useCallback((item, coordinateSystem) => {
    if (!item || !SYSTEMS.includes(coordinateSystem) || !validCoordinate(item[coordinateSystem])) return;
    setSelection({ objectId: objectIdentity(item), system: coordinateSystem });
  }, []);

  const setSortKey = useCallback((key) => {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  const toggleLayer = useCallback((key) => {
    setLayers((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  const resetView = useCallback(() => {
    setSystem(DEFAULT_SYSTEM);
    setRotation(numberOr(chartInfo.rotation, DEFAULT_ROTATION));
    setTilt(clamp(numberOr(chartInfo.tilt, DEFAULT_TILT), -90, 90));
    setLayers(LAYER_PRESETS[DEFAULT_SYSTEM]);
    setSelection((current) => ({ ...current, system: DEFAULT_SYSTEM }));
  }, [chartInfo.rotation, chartInfo.tilt]);

  const handlePointerDown = useCallback((event) => {
    if (event.button !== 0) return;
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      rotation,
      tilt,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }, [rotation, tilt]);

  const handlePointerMove = useCallback((event) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    setRotation(normalizeDegrees(drag.rotation + ((event.clientX - drag.x) * 0.6)) ?? DEFAULT_ROTATION);
    setTilt(clamp(drag.tilt - ((event.clientY - drag.y) * 0.45), -90, 90));
  }, []);

  const handlePointerUp = useCallback((event) => {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    dragRef.current = null;
  }, []);

  if (!open) return null;

  const statusMessage = selectedObject
    ? `Inspecting ${selectedObject.name} in ${SYSTEM_DETAILS[selection.system]?.name || selection.system} coordinates.`
    : 'No coordinate is selected.';
  const hasContent = objects.length > 0;
  const tableSystems = SYSTEMS;

  return (
    <div
      className="fixed inset-0 z-[80] flex items-stretch justify-center bg-black/45 p-0 sm:items-center sm:p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCloseRef.current?.();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        aria-busy={Boolean(loading)}
        tabIndex="-1"
        className="flex h-full max-h-full w-full max-w-6xl flex-col overflow-hidden bg-white shadow-2xl outline-none sm:h-auto sm:max-h-[92vh] sm:rounded-2xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-zinc-200 px-3 py-3 sm:gap-4 sm:px-5 sm:py-4">
          <div className="min-w-0">
            <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-teal-700">
              Astro Clock / Directional
            </div>
            <h2 id={titleId} className="text-lg font-semibold text-zinc-950">Directional 3D</h2>
            <p id={descriptionId} className="mt-1 text-[11px] leading-4 text-zinc-500">
              Drag a sphere or use the sliders to orbit. All systems are shown as independent coordinate views.
            </p>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
              <span>UTC {chartInfo.utc_datetime || 'Unavailable'}</span>
              <span>Lat {formatNumber(chartInfo.latitude, 4)}</span>
              <span>Lon {formatNumber(chartInfo.longitude, 4)}</span>
              <span>Houses {chartInfo.house_system || 'Unavailable'}</span>
            </div>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={() => onCloseRef.current?.()}
            className="flex-none rounded-full border border-zinc-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-600 outline-none hover:bg-zinc-50 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
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

        <div className="min-h-0 overflow-y-auto overflow-x-hidden p-3 sm:p-5">
          <div className="sr-only" aria-live="polite">{statusMessage}</div>

          {loading ? (
            <div
              role="status"
              aria-live="polite"
              className={`mb-3 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-600 ${
                hasContent ? '' : 'flex min-h-[300px] items-center justify-center'
              }`}
            >
              Loading Directional 3D…
            </div>
          ) : null}

          {error ? (
            <div
              role="alert"
              className={`mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700 ${
                hasContent ? '' : 'flex min-h-[300px] flex-col items-center justify-center gap-3 text-center'
              }`}
            >
              <span>{error}</span>
              {onRetry ? (
                <button
                  type="button"
                  onClick={onRetry}
                  className="mt-2 rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-white outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
                >
                  Retry
                </button>
              ) : null}
            </div>
          ) : null}

          {!loading && !error && !hasContent ? (
            <div role="status" className="flex min-h-[300px] items-center justify-center text-sm text-zinc-500">
              No valid Directional objects were returned for this chart.
            </div>
          ) : null}

          {hasContent ? (
            <>
              <DirectionalModelContext
                bodyPolicy={bodyPolicy}
                chartInfo={chartInfo}
                frameContext={frameContext}
              />

              {(invalidObjectCount > 0 || dataGaps.length > 0) ? (
                <aside
                  role="status"
                  className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-[11px] leading-5 text-zinc-600"
                >
                  <div className="font-semibold text-zinc-800">Calculation notes</div>
                  {invalidObjectCount > 0 ? (
                    <div>{invalidObjectCount} malformed object row(s) were rejected.</div>
                  ) : null}
                  {dataGaps.map((gap, index) => <div key={`${index}-${gap}`}>{gap}</div>)}
                </aside>
              ) : null}

              <div className="mb-4 flex flex-wrap items-center gap-2" aria-label="Coordinate system">
                {[...SYSTEMS, 'ALL'].map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={system === option}
                    onClick={() => selectSystem(option)}
                    className={`rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 ${
                      system === option
                        ? 'bg-zinc-900 text-white'
                        : 'border border-zinc-200 text-zinc-600 hover:border-zinc-400'
                    }`}
                  >
                    {option === 'ALL' ? 'All systems' : option}
                  </button>
                ))}
              </div>

              {system === 'ALL' ? (
                <div className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-[11px] leading-5 text-zinc-600">
                  Ecliptic, equatorial, and horizon coordinates use different reference planes. They are separated below so positions are not falsely co-registered.
                </div>
              ) : null}

              <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
                <div className="min-w-0 space-y-4">
                  <div className={system === 'ALL' ? 'grid gap-3 md:grid-cols-3' : ''}>
                    {activeSystems.map((activeSystem) => (
                      <SpherePane
                        key={activeSystem}
                        objects={objects}
                        system={activeSystem}
                        rotation={rotation}
                        tilt={tilt}
                        layers={layers}
                        selectedObjectId={selection.objectId}
                        selectedSystem={selection.system}
                        onPointerDown={handlePointerDown}
                        onPointerMove={handlePointerMove}
                        onPointerUp={handlePointerUp}
                      />
                    ))}
                  </div>

                  <div className="grid gap-3 rounded-lg border border-zinc-200 p-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
                    <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
                      Rotation
                      <input
                        aria-label="Directional rotation"
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
                        aria-label="Directional tilt"
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
                    <button
                      type="button"
                      onClick={resetView}
                      className="rounded-full border border-zinc-200 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-700 outline-none hover:border-zinc-400 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
                    >
                      Reset view
                    </button>
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
                      {relevantLayers.map((key) => {
                        const active = Boolean(layers[key]);
                        return (
                          <button
                            key={key}
                            type="button"
                            aria-pressed={active}
                            onClick={() => toggleLayer(key)}
                            className={`rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 ${
                              active
                                ? 'bg-zinc-900 text-white'
                                : 'border border-zinc-200 text-zinc-600 hover:border-zinc-400'
                            }`}
                          >
                            {LAYER_DETAILS[key]}
                          </button>
                        );
                      })}
                    </div>
                    <p className="mt-2 text-[10px] leading-4 text-zinc-400">
                      Back points controls object and cusp markers only. Reference geometry remains faintly visible for orientation.
                    </p>
                  </div>
                </div>

                <div className="min-w-0 space-y-3">
                  <DirectionalInspector
                    activeSystems={activeSystems}
                    objectsCount={objects.length}
                    payloadSystems={payload?.systems}
                    selectedObject={selectedObject}
                    selectedSystem={selection.system}
                  />

                  <div className="max-h-[380px] max-w-full overflow-auto rounded-xl border border-zinc-200 bg-white">
                    <table className="min-w-[760px] divide-y divide-zinc-100 text-left text-xs">
                      <caption className="sr-only">
                        Directional coordinates. Select a coordinate to inspect an object in that system.
                      </caption>
                      <thead className="sticky top-0 z-10 bg-zinc-50">
                        <tr>
                          <SortHeader
                            activeKey={sort.key}
                            direction={sort.direction}
                            label="Object"
                            sortKey="name"
                            onSort={setSortKey}
                          />
                          {tableSystems.map((itemSystem) => {
                            const details = SYSTEM_DETAILS[itemSystem];
                            return (
                              <React.Fragment key={itemSystem}>
                                <SortHeader
                                  activeKey={sort.key}
                                  direction={sort.direction}
                                  label={`${itemSystem} ${details.longitudeLabel}`}
                                  sortKey={`${itemSystem}.longitude`}
                                  onSort={setSortKey}
                                />
                                <SortHeader
                                  activeKey={sort.key}
                                  direction={sort.direction}
                                  label={`${itemSystem} ${details.latitudeLabel}`}
                                  sortKey={`${itemSystem}.latitude`}
                                  onSort={setSortKey}
                                />
                              </React.Fragment>
                            );
                          })}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 bg-white">
                        {sortedObjects.map((item) => {
                          const itemId = objectIdentity(item);
                          const cusp = isCuspObject(item);
                          const selectedRow = selection.objectId === itemId;
                          return (
                            <tr
                              key={itemId}
                              aria-selected={selectedRow}
                              className={selectedRow ? 'bg-zinc-50' : ''}
                            >
                              <th scope="row" className="whitespace-nowrap px-3 py-2 font-medium text-zinc-900">
                                <span className="flex items-center gap-2">
                                  {!cusp ? (
                                    <span
                                      aria-hidden="true"
                                      className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-zinc-200 text-[13px]"
                                    >
                                      {safeObjectSymbol(item)}
                                    </span>
                                  ) : null}
                                  <span>{item.name}</span>
                                </span>
                              </th>
                              {tableSystems.map((itemSystem) => {
                                const details = SYSTEM_DETAILS[itemSystem];
                                const coord = item[itemSystem];
                                const longitudeAvailable = asFiniteNumber(coord?.longitude) !== null;
                                const latitudeAvailable = item.bfull !== false
                                  && asFiniteNumber(coord?.latitude) !== null;
                                return (
                                  <React.Fragment key={`${itemId}-${itemSystem}`}>
                                    <td className="whitespace-nowrap px-3 py-2 text-zinc-700">
                                      {longitudeAvailable ? (
                                        <button
                                          type="button"
                                          aria-pressed={selection.objectId === itemId && selection.system === itemSystem}
                                          aria-label={`Inspect ${item.name} ${itemSystem} ${details.longitudeLabel} ${formatNumber(coord.longitude)}`}
                                          onClick={() => selectObject(item, itemSystem)}
                                          className="rounded px-1 py-0.5 tabular-nums outline-none hover:bg-zinc-100 focus-visible:ring-2 focus-visible:ring-teal-600"
                                        >
                                          {formatNumber(coord.longitude)}
                                        </button>
                                      ) : (
                                        <span className="text-zinc-400">Unavailable</span>
                                      )}
                                    </td>
                                    <td className="whitespace-nowrap px-3 py-2 text-zinc-700">
                                      {latitudeAvailable ? (
                                        <button
                                          type="button"
                                          aria-pressed={selection.objectId === itemId && selection.system === itemSystem}
                                          aria-label={`Inspect ${item.name} ${itemSystem} ${details.latitudeLabel} ${formatNumber(coord.latitude)}`}
                                          onClick={() => selectObject(item, itemSystem)}
                                          className="rounded px-1 py-0.5 tabular-nums outline-none hover:bg-zinc-100 focus-visible:ring-2 focus-visible:ring-teal-600"
                                        >
                                          {formatNumber(coord.latitude)}
                                        </button>
                                      ) : (
                                        <span className="text-zinc-400">Unavailable</span>
                                      )}
                                    </td>
                                  </React.Fragment>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
