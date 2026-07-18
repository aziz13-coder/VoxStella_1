import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Circle, CircleMarker, GeoJSON, MapContainer, Marker, Polyline, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { AstroClockAPI } from './api.mjs';
import worldCountriesGeoJson from './data/ne_110m_admin_0_countries.json';
import { pollAsyncSession } from './researchPolling.mjs';
import {
  getAstrocartographyTargetLabel,
  getAstrocartographyTargetQuery,
  resolveAstrocartographyTargetQuery,
} from './astrocartographyTargets.mjs';
import {
  getSavedSnapIneligibilityLabel,
  isSavedSnapCalculationEligible,
} from './savedSnapViewModel.mjs';
import MundaneWorkspace from './MundaneWorkspace.jsx';
import WeatherWorkspace from './WeatherWorkspace.jsx';
import {
  ConsoleBracketEyebrow,
  ConsoleCommandBand,
  ConsoleEmptyState,
  ConsoleModeTabs,
  ConsoleRailSection,
  researchWorkspaceCls,
} from './researchWorkspacePrimitives.jsx';

const BODY_OPTIONS = [
  { id: 'Sun' },
  { id: 'Moon' },
  { id: 'Mercury' },
  { id: 'Venus' },
  { id: 'Mars' },
  { id: 'Jupiter' },
  { id: 'Saturn' },
  { id: 'Uranus' },
  { id: 'Neptune' },
  { id: 'Pluto' },
  { id: 'North Node' },
  { id: 'Chiron' },
];
const ANGLE_OPTIONS = ['MC', 'IC', 'ASC', 'DSC'];
const DEFAULT_VIEW = { center: [20, 0], zoom: 2 };
const WORLD_BOUNDS = [[-89, -180], [89, 180]];
const BODY_LABEL_META = {
  Sun: { short: 'Su', symbol: '☉' },
  Moon: { short: 'Mo', symbol: '☽' },
  Mercury: { short: 'Me', symbol: '☿' },
  Venus: { short: 'Ve', symbol: '♀' },
  Mars: { short: 'Ma', symbol: '♂' },
  Jupiter: { short: 'Ju', symbol: '♃' },
  Saturn: { short: 'Sa', symbol: '♄' },
  Uranus: { short: 'Ur', symbol: '♅' },
  Neptune: { short: 'Ne', symbol: '♆' },
  Pluto: { short: 'Pl', symbol: '♇' },
  'North Node': { short: 'NN', symbol: '☊' },
  Chiron: { short: 'Ch', symbol: '⚷' },
};
const MAP_THEME = {
  water: '#cfe0ee',
  land: '#f6efd8',
  coast: '#beb59d',
  grid: '#9fb0bb',
  frame: '#a8bcc8',
};
const GRATICULE_LINES = (() => {
  const meridians = [];
  const parallels = [];
  for (let longitude = -150; longitude <= 150; longitude += 30) {
    meridians.push([
      [-85, longitude],
      [85, longitude],
    ]);
  }
  for (let latitude = -60; latitude <= 60; latitude += 30) {
    parallels.push([
      [latitude, -180],
      [latitude, 180],
    ]);
  }
  return { meridians, parallels };
})();
const ATLAS_RESOLUTION_OPTIONS = [
  {
    id: 'coarse',
    label: 'Coarse',
    hint: 'Fastest scan. Cities of 500,000+, plus capitals and first-level admin centers even below that size.',
  },
  {
    id: 'standard',
    label: 'Standard',
    hint: 'Balanced scan. Good default for normal PathFinder work.',
  },
  {
    id: 'fine',
    label: 'Fine',
    hint: 'Denser scan. Adds more mid-size cities and a deeper shortlist.',
  },
  {
    id: 'ultra',
    label: 'Ultra',
    hint: 'Deepest atlas scan. Uses the full shipped catalog and live query augmentation.',
  },
];
const WORKSPACE_TABS = [
  { id: 'map', label: 'Map' },
  { id: 'intersections', label: 'Intersections' },
  { id: 'local-space', label: 'Local Space' },
  { id: 'report', label: 'Report' },
];
const ANALYSIS_MODE_OPTIONS = [
  { id: 'astrocartography', label: 'Astrocartography' },
  { id: 'mundane', label: 'Mundane' },
  { id: 'weather', label: 'Weather' },
];
const ATLAS_CONTINENT_OPTIONS = [
  { id: '', label: 'All regions' },
  { id: 'AF', label: 'Africa' },
  { id: 'AS', label: 'Asia' },
  { id: 'EU', label: 'Europe' },
  { id: 'NA', label: 'North America' },
  { id: 'OC', label: 'Oceania' },
  { id: 'SA', label: 'South America' },
];
const SPECIALIST_GOAL_IDS = new Set([
  'accident_prone',
  'body_presence',
  'love_commitment',
  'money_stable_income',
  'gambling_luck',
  'career_public_profile',
  'home_retreat',
  'health_risk',
]);
const EXPERIMENTAL_GOAL_META = {
  health_risk: {
    label: 'Experimental health-pressure interpretation',
    caveat: 'Interpretive research only. It is not medical guidance or a prediction of illness.',
  },
  accident_prone: {
    label: 'Experimental accident-pressure interpretation',
    caveat: 'Interpretive research only. It is not a safety forecast or a substitute for practical risk assessment.',
  },
  gambling_luck: {
    label: 'Experimental speculation interpretation',
    caveat: 'Interpretive research only. It does not predict winnings and is not financial or gambling advice.',
  },
  travel_fun: {
    label: 'Experimental travel interpretation',
    caveat: 'Interpretive research only. Use practical safety, budget, and travel information when choosing a destination.',
  },
  travel_relax: {
    label: 'Experimental travel interpretation',
    caveat: 'Interpretive research only. Use practical safety, health, budget, and travel information when choosing a destination.',
  },
};
const LOCAL_SPACE_OPTIONS = [
  { id: 'relocated', label: 'Relocated' },
  { id: 'natal', label: 'Natal' },
];
const HOUSE_SYSTEM_LABELS = {
  R: 'Regiomontanus',
  P: 'Placidus',
  E: 'Equal',
  W: 'Whole Sign',
  O: 'Porphyry',
  C: 'Campanus',
  K: 'Koch',
  T: 'Topocentric',
};
const GOAL_GROUP_LABELS = {
  broad: 'Core Goals',
  specialist: 'Specialist Variants',
};
const astroSectionCardCls = researchWorkspaceCls.sectionCardCls;
const astroNestedCardCls = researchWorkspaceCls.nestedCardCls;
const astroMutedPanelCls = researchWorkspaceCls.mutedPanelCls;
const astroBandCls = researchWorkspaceCls.commandBandCls;
const astroInputCls = researchWorkspaceCls.inputCls;
const astroHeaderDividerCls = 'border-b border-zinc-200/85 pb-3 dark:border-zinc-700/80';
const astroSectionLabelCls = 'font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500 dark:text-zinc-400';
const astroMetaTextCls = 'text-[11px] leading-5 text-zinc-500 dark:text-zinc-400';
const astroBodyTextCls = 'text-sm leading-6 text-zinc-600 dark:text-zinc-300';
const EMPTY_ITEMS = [];
let astrocartographyGoalOptionsCache = null;
let astrocartographyGoalOptionsPromise = null;

function filterFrontendGoalOptions(goals) {
  if (!Array.isArray(goals)) return [];
  return goals.filter((goal) => {
    const status = String(goal?.status || 'active').trim().toLowerCase();
    return status === 'active' || status === 'experimental';
  });
}

function getGoalVariantTier(goal) {
  const goalId = String(goal?.id || '').trim().toLowerCase();
  if (SPECIALIST_GOAL_IDS.has(goalId)) return 'specialist';
  return 'broad';
}

function formatGoalFamilyLabel(goalFamily) {
  const raw = String(goalFamily || '').trim();
  if (!raw) return 'General';
  return raw
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function MapViewport({ target }) {
  const map = useMap();
  useEffect(() => {
    if (!target || typeof target.latitude !== 'number' || typeof target.longitude !== 'number') return;
    map.setView([target.latitude, target.longitude], 4, { animate: true });
  }, [map, target]);
  return null;
}

function NeutralWorldBaseMap() {
  return (
    <>
      <GeoJSON
        data={worldCountriesGeoJson}
        interactive={false}
        style={() => ({
          color: MAP_THEME.coast,
          weight: 0.8,
          opacity: 0.9,
          fillColor: MAP_THEME.land,
          fillOpacity: 1,
        })}
      />
      {GRATICULE_LINES.meridians.map((positions, index) => (
        <Polyline
          key={`graticule-meridian-${index}`}
          positions={positions}
          interactive={false}
          pathOptions={{ color: MAP_THEME.grid, weight: 0.55, opacity: 0.45, dashArray: '2 8' }}
        />
      ))}
      {GRATICULE_LINES.parallels.map((positions, index) => (
        <Polyline
          key={`graticule-parallel-${index}`}
          positions={positions}
          interactive={false}
          pathOptions={{ color: MAP_THEME.grid, weight: 0.55, opacity: 0.38, dashArray: '2 8' }}
        />
      ))}
    </>
  );
}

function interpolatePointAtLatitude(pointA, pointB, targetLatitude) {
  const latA = Number(pointA?.[0]);
  const lonA = Number(pointA?.[1]);
  const latB = Number(pointB?.[0]);
  const lonB = Number(pointB?.[1]);
  if (![latA, lonA, latB, lonB, targetLatitude].every(Number.isFinite)) return null;
  if (latA === latB) {
    return [targetLatitude, lonA];
  }
  const t = (targetLatitude - latA) / (latB - latA);
  if (t < 0 || t > 1) return null;
  return [targetLatitude, lonA + ((lonB - lonA) * t)];
}

function buildLineLabelCoordinate(line, bounds, placement) {
  if (!line || !bounds) return null;
  const north = Number(bounds.getNorth());
  const south = Number(bounds.getSouth());
  const east = Number(bounds.getEast());
  const west = Number(bounds.getWest());
  const latitudeMargin = Math.min(8, Math.max(2, Math.abs(north - south) * 0.08));
  const targetLatitude = placement === 'south' ? south + latitudeMargin : north - latitudeMargin;
  const segments = Array.isArray(line.segments) ? line.segments : [];
  const fallbackPoints = [];

  for (const segment of segments) {
    if (!Array.isArray(segment) || segment.length < 2) continue;
    for (let index = 0; index < segment.length - 1; index += 1) {
      const pointA = segment[index];
      const pointB = segment[index + 1];
      const latA = Number(pointA?.[0]);
      const latB = Number(pointB?.[0]);
      if (![latA, latB].every(Number.isFinite)) continue;
      const minLatitude = Math.min(latA, latB);
      const maxLatitude = Math.max(latA, latB);
      if (targetLatitude < minLatitude || targetLatitude > maxLatitude) {
        const candidate = placement === 'south'
          ? (latA < latB ? pointA : pointB)
          : (latA > latB ? pointA : pointB);
        const latitude = Number(candidate?.[0]);
        const longitude = Number(candidate?.[1]);
        if (
          Number.isFinite(latitude) &&
          Number.isFinite(longitude) &&
          latitude >= south &&
          latitude <= north &&
          longitude >= west &&
          longitude <= east
        ) {
          fallbackPoints.push([latitude, longitude]);
        }
        continue;
      }
      const interpolated = interpolatePointAtLatitude(pointA, pointB, targetLatitude);
      const longitude = Number(interpolated?.[1]);
      if (!interpolated || !Number.isFinite(longitude)) continue;
      if (longitude < west || longitude > east) continue;
      return interpolated;
    }
  }

  if (!fallbackPoints.length) return null;
  fallbackPoints.sort((left, right) => {
    const leftDelta = Math.abs(Number(left?.[0] || 0) - targetLatitude);
    const rightDelta = Math.abs(Number(right?.[0] || 0) - targetLatitude);
    return leftDelta - rightDelta;
  });
  return fallbackPoints[0];
}

function buildLineLabelIcon(line, rowIndex, variant) {
  const bodyMeta = BODY_LABEL_META[String(line?.body || '')] || {};
  const symbol = bodyMeta.symbol || bodyMeta.short || String(line?.body || '').slice(0, 2);
  const angle = String(line?.angle || '');
  const body = String(line?.body || '');
  const color = String(line?.color || '#64748b');
  const isTransit = variant === 'transit';
  const translateY = isTransit ? (14 + (rowIndex * 18)) : (-14 - (rowIndex * 18));
  const background = isTransit ? 'rgba(255,255,255,0.78)' : 'rgba(255,255,255,0.92)';
  const text = isTransit ? '#374151' : '#1f2937';

  return L.divIcon({
    className: 'astrocartography-line-label-marker',
    iconSize: [0, 0],
    iconAnchor: [0, 0],
    html: `
      <div style="
        transform: translate(-50%, ${translateY}px);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        pointer-events: none;
        white-space: nowrap;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.78);
        background: ${background};
        color: ${text};
        box-shadow: 0 0 0 1px ${color}55 inset, 0 1px 3px rgba(15,23,42,0.18);
        padding: 2px 6px 2px 4px;
        font-size: 10px;
        font-weight: 600;
        line-height: 1;
        letter-spacing: 0.03em;
        backdrop-filter: blur(2px);
      " title="${body} ${angle}">
        <span style="
          display:inline-flex;
          align-items:center;
          justify-content:center;
          width:15px;
          height:15px;
          min-width:15px;
          border-radius:999px;
          background:rgba(255,255,255,0.92);
          box-shadow:0 0 0 1px ${color}55 inset;
          color:${color};
          font-size:11px;
          line-height:1;
          text-align:center;
        ">${symbol}</span>
        <span style="
          display:inline-flex;
          align-items:center;
          justify-content:center;
          min-height:15px;
          font-size:9px;
          text-transform:uppercase;
          letter-spacing:0.12em;
          line-height:1;
        ">${angle}</span>
      </div>
    `,
  });
}

function DynamicLineLabels({ lines, placement = 'north', variant = 'natal' }) {
  const map = useMap();
  const [viewTick, setViewTick] = useState(0);

  useEffect(() => {
    const update = () => setViewTick((value) => value + 1);
    map.on('zoomend moveend resize', update);
    return () => {
      map.off('zoomend moveend resize', update);
    };
  }, [map]);

  const visibleLabels = useMemo(() => {
    const bounds = map.getBounds();
    const source = Array.isArray(lines) ? lines : [];
    const anchors = source
      .map((line) => {
        const point = buildLineLabelCoordinate(line, bounds, placement);
        if (!point) return null;
        const containerPoint = map.latLngToContainerPoint(point);
        return {
          id: String(line?.id || `${line?.body || 'line'}-${line?.angle || 'angle'}`),
          line,
          point,
          x: Number(containerPoint?.x || 0),
        };
      })
      .filter(Boolean)
      .sort((left, right) => left.x - right.x);

    let lastX = -Infinity;
    let rowIndex = 0;
    return anchors.map((item) => {
      if (Math.abs(item.x - lastX) < 58) {
        rowIndex += 1;
      } else {
        rowIndex = 0;
      }
      lastX = item.x;
      return { ...item, rowIndex: rowIndex % 4 };
    });
  }, [lines, map, placement, viewTick]);

  return (
    <>
      {visibleLabels.map((item) => (
        <Marker
          key={`${variant}-${placement}-${item.id}`}
          position={item.point}
          icon={buildLineLabelIcon(item.line, item.rowIndex, variant)}
          interactive={false}
          keyboard={false}
        />
      ))}
    </>
  );
}

function TargetPin({ target }) {
  if (!target || typeof target.latitude !== 'number' || typeof target.longitude !== 'number') return null;
  const label = getTargetDisplayLabel(target, 'Selected location');
  return (
    <CircleMarker
      center={[target.latitude, target.longitude]}
      radius={7}
      pathOptions={{ color: '#0f172a', weight: 2, fillColor: '#f8fafc', fillOpacity: 0.95 }}
    >
      <Popup>
        <div className="text-sm">
          <div className="font-medium">{label}</div>
          <div>{target.latitude.toFixed(4)}, {target.longitude.toFixed(4)}</div>
        </div>
      </Popup>
    </CircleMarker>
  );
}

function formatCompactTimestamp(value, timezone) {
  if (!value) return '';
  try {
    const dt = new Date(value);
    return dt.toLocaleString('en-GB', {
      hour12: false,
      timeZone: timezone || undefined,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch (_) {
    return String(value);
  }
}

function describeAstrocartographyError(error, fallbackMessage) {
  const message =
    String(error?.message || '').trim()
    || String(error?.detail || '').trim()
    || fallbackMessage;
  const incidentId = String(error?.incidentId || error?.payload?.incident_id || '').trim();
  if (!incidentId) return message;
  return `${message} [incident ${incidentId}]`;
}

function formatServiceError(value, fallbackMessage) {
  if (typeof value === 'string' && value.trim()) return value.trim();
  if (value && typeof value === 'object') {
    const message = [
      value.message,
      value.detail,
      value.error,
    ].find((item) => typeof item === 'string' && item.trim());
    const code = String(value.code || value.error_code || '').trim();
    if (message) return code ? `${code}: ${message.trim()}` : message.trim();
    if (code) return code;
  }
  return fallbackMessage;
}

function getAtlasProgressPercent(progress) {
  const value = Number(progress?.percent);
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value * 100)));
}

function getTargetCatalogId(target) {
  if (!target || typeof target !== 'object') return '';
  const explicitId = String(
    target.candidate_id
    || target.target_id
    || target.catalog_id
    || ''
  ).trim();
  if (explicitId) return explicitId;
  const geonameId = String(target.geonameid || '').trim();
  if (geonameId) {
    return geonameId.startsWith('geonames:') ? geonameId : `geonames:${geonameId}`;
  }
  return String(target.id || '').trim();
}

function getTargetDisplayLabel(target, fallback = 'Selected target') {
  const label = getAstrocartographyTargetLabel(target);
  if (label) return label;
  const latitude = Number(target?.latitude);
  const longitude = Number(target?.longitude);
  if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
    return `Coordinates ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
  }
  return fallback;
}

function buildCompareKey(target) {
  if (!target) return '';
  const catalogId = getTargetCatalogId(target);
  if (catalogId) return `catalog:${catalogId}`;
  return [
    target.latitude,
    target.longitude,
    getTargetDisplayLabel(target, ''),
  ].map((value) => String(value ?? '')).join('|');
}

function buildRankingTarget(entry) {
  const source = entry?.target && typeof entry.target === 'object' ? entry.target : (entry || {});
  const catalogId = getTargetCatalogId(source)
    || getTargetCatalogId(entry)
    || getTargetCatalogId(entry?.atlas_city);
  return {
    ...source,
    ...(catalogId ? { candidate_id: catalogId } : {}),
    label: getTargetDisplayLabel(source, String(entry?.label || entry?.query || 'Selected coordinates')),
    query: getAstrocartographyTargetQuery(source) || String(entry?.query || entry?.label || '').trim(),
    latitude: source.latitude ?? entry?.latitude,
    longitude: source.longitude ?? entry?.longitude,
  };
}

function resolveCompareRankingIdentity(entry, compareResult, compareEntries) {
  const directTarget = buildRankingTarget(entry);
  const hasDirectIdentity = Boolean(
    getTargetCatalogId(directTarget)
    || (
      Number.isFinite(Number(directTarget.latitude))
      && Number.isFinite(Number(directTarget.longitude))
    )
  );
  if (hasDirectIdentity) return { target: directTarget, ambiguous: false };

  const entryQuery = String(entry?.query || entry?.label || '').trim();
  const entryScoreRaw = entry?.location_score?.score ?? entry?.score;
  const entryScore = entryScoreRaw == null || String(entryScoreRaw).trim() === ''
    ? Number.NaN
    : Number(entryScoreRaw);
  const responseMatches = (Array.isArray(compareResult?.targets) ? compareResult.targets : [])
    .filter((candidate) => {
      const candidateTarget = candidate?.target || candidate;
      const candidateQuery = getAstrocartographyTargetQuery(candidateTarget)
        || getTargetDisplayLabel(candidateTarget, '');
      if (!entryQuery || candidateQuery !== entryQuery) return false;
      const candidateScoreRaw = candidate?.location_score?.score ?? candidate?.score;
      const candidateScore = candidateScoreRaw == null || String(candidateScoreRaw).trim() === ''
        ? Number.NaN
        : Number(candidateScoreRaw);
      return !Number.isFinite(entryScore)
        || !Number.isFinite(candidateScore)
        || candidateScore === entryScore;
    });
  if (responseMatches.length === 1) {
    return {
      target: buildRankingTarget(responseMatches[0]),
      ambiguous: false,
    };
  }

  const savedMatches = (Array.isArray(compareEntries) ? compareEntries : [])
    .filter((candidate) => {
      const candidateTarget = candidate?.target || {};
      const candidateQuery = getAstrocartographyTargetQuery(candidateTarget)
        || getTargetDisplayLabel(candidateTarget, '');
      return Boolean(entryQuery && candidateQuery === entryQuery);
    });
  if (savedMatches.length === 1) {
    return {
      target: buildRankingTarget(savedMatches[0]),
      ambiguous: false,
    };
  }

  return {
    target: directTarget,
    ambiguous: responseMatches.length > 1 || savedMatches.length > 1,
  };
}

function targetsReferToSameLocation(left, right) {
  const leftId = getTargetCatalogId(left);
  const rightId = getTargetCatalogId(right);
  if (leftId && rightId) return leftId === rightId;

  const leftLatitude = Number(left?.latitude);
  const leftLongitude = Number(left?.longitude);
  const rightLatitude = Number(right?.latitude);
  const rightLongitude = Number(right?.longitude);
  if ([leftLatitude, leftLongitude, rightLatitude, rightLongitude].every(Number.isFinite)) {
    return Math.abs(leftLatitude - rightLatitude) < 1e-8
      && Math.abs(leftLongitude - rightLongitude) < 1e-8;
  }

  const leftQuery = getAstrocartographyTargetQuery(left) || getTargetDisplayLabel(left, '');
  const rightQuery = getAstrocartographyTargetQuery(right) || getTargetDisplayLabel(right, '');
  return Boolean(leftQuery && rightQuery && leftQuery === rightQuery);
}

function dedupeCanonicalEvidence(items) {
  if (!Array.isArray(items)) return [];
  const seen = new Set();
  return items.filter((item, index) => {
    const canonicalId = String(item?.canonical_event_id || item?.id || `row-${index}`);
    const eventKind = String(item?.event_kind || item?.kind || 'unspecified');
    const key = `${canonicalId}::${eventKind}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function getEvidenceKindLabel(item, fallback) {
  const token = String(item?.event_kind || '').trim().toLowerCase();
  return {
    'angular-line-crossing': 'Line crossing',
    'angular-line-proximity-blend': 'Proximity blend',
    'paran-crossing-point': 'Paran point',
    'paran-latitude-corridor': 'Paran corridor',
  }[token] || fallback;
}

function firstNonEmptyObject(...values) {
  return values.find((value) => (
    value
    && typeof value === 'object'
    && !Array.isArray(value)
    && Object.keys(value).length > 0
  )) || {};
}

function getZoneBadgeCls(zone) {
  if (zone === 'primary') {
    return 'border-emerald-300/80 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-200';
  }
  if (zone === 'extended') {
    return 'border-amber-300/80 bg-amber-50 text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200';
  }
  return 'border-zinc-300/80 bg-zinc-50 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700/30 dark:text-zinc-200';
}

function getSignalBadgeCls(score, higherIsWorse = false) {
  if (score >= 70) {
    return higherIsWorse
      ? 'border-rose-300/80 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-200'
      : 'border-emerald-300/80 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-200';
  }
  if (score >= 35) {
    return 'border-amber-300/80 bg-amber-50 text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200';
  }
  return higherIsWorse
    ? 'border-emerald-300/80 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-200'
    : 'border-zinc-300/80 bg-zinc-50 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700/30 dark:text-zinc-200';
}

function getMapScoreColors(score, higherIsWorse = false) {
  if (higherIsWorse) {
    if (score >= 70) return { color: '#be123c', fillColor: '#fb7185' };
    if (score >= 35) return { color: '#b45309', fillColor: '#f59e0b' };
    return { color: '#047857', fillColor: '#34d399' };
  }
  if (score >= 70) return { color: '#047857', fillColor: '#34d399' };
  if (score >= 35) return { color: '#b45309', fillColor: '#f59e0b' };
  return { color: '#475569', fillColor: '#94a3b8' };
}

function getSignalMetricTone(score, higherIsWorse = false) {
  if (score >= 70) return higherIsWorse ? 'danger' : 'success';
  if (score >= 35) return 'warning';
  return higherIsWorse ? 'success' : 'default';
}

function normalizeOrdinalLabel(value) {
  const token = String(value || '').trim().toLowerCase().replace(/[\s-]+/g, '_');
  if (token.includes('insufficient') || token === 'none' || token === 'unavailable') return 'Insufficient';
  if (token.includes('weak') || token === 'low') return 'Weak';
  if (token.includes('mixed') || token === 'moderate' || token === 'medium') return 'Mixed';
  if (token.includes('strong') || token === 'high') return 'Strong';
  return '';
}

export function getAstrocartographyOrdinal(payload, { rankingEligible } = {}) {
  if (rankingEligible === false) return 'Insufficient';
  const source = payload && typeof payload === 'object' ? payload : {};
  const explicit = [
    source.ordinal_strength,
    source.strength_ordinal,
    source.evidence_strength,
    source.signal_strength,
    source.strength?.label,
    source.evidence?.ordinal,
    source.location_score?.ordinal_strength,
  ].map(normalizeOrdinalLabel).find(Boolean);
  if (explicit) return explicit;

  const scoreValue = source.score
    ?? source.location_score?.score
    ?? source.reading?.signal_score
    ?? (typeof payload === 'number' ? payload : null);
  if (scoreValue == null || !Number.isFinite(Number(scoreValue))) return 'Insufficient';
  const score = Number(scoreValue);
  if (score <= 0) return 'Insufficient';
  if (score < 35) return 'Weak';
  if (score < 70) return 'Mixed';
  return 'Strong';
}

export function getAstrocartographyRankStability(payload) {
  const source = payload && typeof payload === 'object' ? payload : {};
  const value = source.rank_stability ?? source.ranking_stability ?? source.stability;
  if (value == null) return { label: 'Not assessed', detail: '' };
  if (typeof value === 'boolean') {
    return {
      label: value ? 'Stable' : 'Unstable',
      detail: value ? 'Rank held across reported checks.' : 'Rank changed across reported checks.',
    };
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    const normalized = value > 1 ? value / 100 : value;
    return {
      label: normalized >= 0.75 ? 'Stable' : (normalized >= 0.45 ? 'Mixed' : 'Unstable'),
      detail: `${Math.round(Math.max(0, Math.min(1, normalized)) * 100)}% reported stability`,
    };
  }
  if (typeof value === 'string') {
    const label = value.trim().replace(/[_-]+/g, ' ');
    return { label: label ? label.charAt(0).toUpperCase() + label.slice(1) : 'Not assessed', detail: '' };
  }
  const labelValue = value.label || value.status || value.ordinal || value.classification;
  const label = String(labelValue || 'Not assessed').trim().replace(/[_-]+/g, ' ');
  const rankRange = Array.isArray(value.rank_range)
    ? value.rank_range.join('–')
    : (
      value.rank_interval?.best != null && value.rank_interval?.worst != null
        ? `${value.rank_interval.best}–${value.rank_interval.worst}`
        : ''
    );
  const reportedDetail = String(
    value.detail
    || value.reason
    || value.summary
    || (rankRange ? `Reported rank range ${rankRange}` : '')
  ).trim();
  const candidateCount = Number(value.candidate_count);
  const scopeCandidateCount = Number(value.scope_candidate_count);
  const hasCandidateCount = Number.isFinite(candidateCount) && candidateCount > 0;
  const hasScopeCandidateCount = Number.isFinite(scopeCandidateCount) && scopeCandidateCount > 0;
  const boundedScope = value.bounded_scope === true || (
    hasCandidateCount
    && hasScopeCandidateCount
    && scopeCandidateCount > candidateCount
  );
  const boundedScopeDetail = boundedScope && hasCandidateCount && hasScopeCandidateCount
    ? `evaluated among ${candidateCount} of ${scopeCandidateCount} candidates`
    : '';
  const detail = [reportedDetail, boundedScopeDetail].filter(Boolean).join(' · ');
  const scopeCoverage = Number(value.scope_coverage);
  return {
    label: label ? label.charAt(0).toUpperCase() + label.slice(1) : 'Not assessed',
    detail,
    boundedScope,
    candidateCount: hasCandidateCount ? candidateCount : null,
    scopeCandidateCount: hasScopeCandidateCount ? scopeCandidateCount : null,
    scopeCoverage: Number.isFinite(scopeCoverage) ? scopeCoverage : null,
  };
}

function formatStatusLabel(value, fallback = '') {
  const text = String(value || fallback || '').trim().replace(/[_-]+/g, ' ');
  if (!text) return '';
  return text.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function getAstrocartographyBirthTimeAssessment(...sources) {
  const candidates = [];
  sources.filter(Boolean).forEach((source) => {
    if (!source || typeof source !== 'object') return;
    candidates.push(
      source.birth_time,
      source.birth_time_accuracy,
      source.calculation?.birth_time,
      source.provenance?.birth_time,
      source.summary?.certification,
      source.certification,
    );
    if (
      typeof source.ranking_eligible === 'boolean'
      || source.ranking_eligibility
      || source.uncertainty_minutes != null
    ) {
      candidates.push(source);
    }
  });
  const payload = candidates.find((item) => (
    item
    && typeof item === 'object'
    && (
      typeof item.ranking_eligible === 'boolean'
      || typeof item.eligible_for_ranking === 'boolean'
      || item.ranking_eligibility
    )
  )) || candidates.find((item) => item && typeof item === 'object') || null;
  if (!payload) {
    return {
      status: 'not_reported',
      accuracyLabel: 'Not reported',
      confidenceLabel: 'Unknown uncertainty',
      uncertaintyLabel: '',
      rankingEligible: null,
      rankingLabel: 'Eligibility not reported',
      reason: 'This snap does not report a birth-time accuracy assessment.',
      warnings: [],
    };
  }

  const status = String(payload.status || payload.accuracy_status || 'not_reported').trim().toLowerCase();
  const confidence = String(payload.confidence || payload.accuracy || '').trim().toLowerCase();
  const eligibilityValue = payload.ranking_eligible ?? payload.eligible_for_ranking;
  const eligibilityText = String(payload.ranking_eligibility || '').trim().toLowerCase();
  let rankingEligible = typeof eligibilityValue === 'boolean' ? eligibilityValue : null;
  if (rankingEligible == null && eligibilityText) {
    if (['eligible', 'allowed', 'rankable', 'confirmed', 'provisional'].includes(eligibilityText)) rankingEligible = true;
    if (
      ['ineligible', 'blocked', 'not_eligible', 'inspection_only', 'regional_only'].includes(eligibilityText)
      || eligibilityText.startsWith('ineligible_')
    ) {
      rankingEligible = false;
    }
  }
  if (rankingEligible == null && ['certified_source', 'certificate', 'certified', 'aa', 'record', 'family_exact'].includes(status)) {
    rankingEligible = true;
  }
  if (rankingEligible == null && ['insufficient_data', 'unresolved_rectification', 'unknown'].includes(status)) {
    rankingEligible = false;
  }

  const uncertaintyRaw = payload.uncertainty_minutes;
  const uncertaintyMinutes = uncertaintyRaw != null && String(uncertaintyRaw).trim() !== ''
    ? Number(uncertaintyRaw)
    : Number.NaN;
  const searchWindowRaw = payload.search_window_minutes;
  const searchWindowMinutes = searchWindowRaw != null && String(searchWindowRaw).trim() !== ''
    ? Number(searchWindowRaw)
    : Number.NaN;
  if (rankingEligible == null && status === 'approximate') {
    rankingEligible = Number.isFinite(uncertaintyMinutes) ? uncertaintyMinutes <= 5 : false;
  }
  if (rankingEligible == null && status === 'rectified_candidate') {
    rankingEligible = Number.isFinite(uncertaintyMinutes) ? uncertaintyMinutes <= 5 : true;
  }
  const warnings = Array.isArray(payload.warnings)
    ? payload.warnings.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  return {
    status,
    accuracyLabel: String(payload.label || payload.accuracy_label || formatStatusLabel(status, 'Not reported')),
    confidenceLabel: confidence ? `${formatStatusLabel(confidence)} confidence` : 'Confidence not reported',
    uncertaintyLabel: Number.isFinite(uncertaintyMinutes)
      ? `±${Math.max(0, uncertaintyMinutes)} min`
      : (
        String(payload.uncertainty || '').trim()
        || (Number.isFinite(searchWindowMinutes)
          ? `${Math.max(0, searchWindowMinutes)} min search window`
          : '')
      ),
    rankingEligible,
    rankingLabel: rankingEligible === true
      ? 'Ranking eligible'
      : (rankingEligible === false ? 'Inspection only · ranking unavailable' : 'Eligibility not reported'),
    reason: String(
      payload.reason
      || payload.ranking_reason
      || (payload.ranking_eligibility
        ? `Ranking policy: ${formatStatusLabel(payload.ranking_eligibility)}`
        : '')
    ).trim(),
    warnings,
  };
}

function getLocalSpaceOrigin(localSpace, fallbackTarget = null) {
  const origin = localSpace?.origin || {};
  const latitude = Number(origin.latitude ?? localSpace?.origin_latitude ?? fallbackTarget?.latitude);
  const longitude = Number(origin.longitude ?? localSpace?.origin_longitude ?? fallbackTarget?.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  return {
    ...(fallbackTarget || {}),
    label: String(origin.label || localSpace?.origin_label || fallbackTarget?.label || 'Local Space origin'),
    latitude,
    longitude,
  };
}

function getToneCls(tone) {
  if (tone === 'support' || tone === 'goal') {
    return 'border-emerald-200/90 bg-emerald-50/90 dark:border-emerald-500/30 dark:bg-emerald-500/10';
  }
  if (tone === 'activation') {
    return 'border-zinc-300/90 bg-zinc-100/90 dark:border-zinc-600 dark:bg-zinc-800/50';
  }
  if (tone === 'caution') {
    return 'border-rose-200/90 bg-rose-50/90 dark:border-rose-500/30 dark:bg-rose-500/10';
  }
  return 'border-zinc-200/90 bg-zinc-50/84 dark:border-zinc-700 dark:bg-zinc-900/40';
}

function WorkspaceTabs({ value, onChange }) {
  return <ConsoleModeTabs options={WORKSPACE_TABS} value={value} onChange={onChange} wrap fullWidth />;
}

function MapHudPill({ children, tone = 'default' }) {
  const toneCls = {
    default: 'border-white/80 bg-white/92 text-zinc-700',
    muted: 'border-zinc-300/75 bg-zinc-50/92 text-zinc-600',
    accent: 'border-zinc-300/85 bg-zinc-100/94 text-zinc-700',
    success: 'border-emerald-200/85 bg-emerald-50/94 text-emerald-700',
  }[tone] || 'border-white/80 bg-white/92 text-zinc-700';

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] shadow-none backdrop-blur-sm ${toneCls}`}>
      {children}
    </span>
  );
}

function MetricChip({ label, value, tone = 'default' }) {
  if (!value && value !== 0) return null;
  const toneCls = {
    default: 'border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900/40 dark:text-zinc-200',
    accent: 'border-zinc-300 bg-zinc-50 text-zinc-800 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
    warning: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200',
    danger: 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200',
  }[tone] || 'border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900/40 dark:text-zinc-200';

  return (
    <div className={`min-w-[5.5rem] rounded-[4px] border px-3 py-2.5 ${toneCls}`}>
      {label ? <div className="font-mono text-[9px] font-semibold uppercase tracking-[0.18em] opacity-70">{label}</div> : null}
      <div className={`${label ? 'mt-1.5' : ''} text-sm font-medium leading-tight tracking-[-0.01em]`}>{value}</div>
    </div>
  );
}

function WorkspaceHeader({ eyebrow, title, description, metrics = [] }) {
  const items = Array.isArray(metrics) ? metrics.filter(Boolean) : [];
  return (
    <div className="border-b border-zinc-200/90 pb-4 dark:border-zinc-700/80">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-3xl">
          {eyebrow ? <ConsoleBracketEyebrow>{eyebrow}</ConsoleBracketEyebrow> : null}
          <h3 className="mt-2 font-serif text-[1.35rem] font-medium leading-tight tracking-[-0.025em] text-zinc-900 dark:text-zinc-100">{title}</h3>
          {description ? <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600 dark:text-zinc-300">{description}</p> : null}
        </div>
        {items.length ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            {items.map((item) => (
              <MetricChip key={`${item.label}-${item.value}`} label={item.label} value={item.value} tone={item.tone} />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function WorkspaceEmptyState({ title, detail }) {
  return <ConsoleEmptyState title={title} detail={detail} module="astrocartography" />;
}

function SelectedCitySummaryCard({
  target,
  selectedGoal,
  targetResult,
  viewMode,
  onAddToCompare,
  actionButtonCls,
  rankingEligible,
}) {
  if (!target) {
    return (
      <div className={`${astroMutedPanelCls} text-sm text-zinc-600 dark:text-zinc-300`}>
        No city selected.
      </div>
    );
  }

  const targetLabel = getTargetDisplayLabel(target, 'Selected location');
  const activeMode = viewMode === 'transit' && targetResult?.transit ? 'Transit overlay' : 'Natal baseline';
  const locationScore = Number(targetResult?.location_score?.score || 0);
  const scoreInterval = targetResult?.location_score?.score_interval;
  const scoreLow = Number(scoreInterval?.low);
  const scoreHigh = Number(scoreInterval?.high);
  const hasScoreInterval = Number.isFinite(scoreLow) && Number.isFinite(scoreHigh);
  const natalSignal = Number(targetResult?.natal?.reading?.signal_score || 0);
  const transitSignal = Number(targetResult?.transit?.reading?.signal_score || 0);
  const higherIsWorse = selectedGoal?.score_polarity === 'higher_is_worse';
  const leadFactor =
    (higherIsWorse ? targetResult?.location_score?.top_cautions?.[0]?.label : '')
    || targetResult?.location_score?.top_supports?.[0]?.label
    || targetResult?.natal?.reading?.lead_line?.label
    || '';
  const scoreLabel = higherIsWorse ? 'Modeled pressure' : 'Model signal';
  const scoreOrdinal = getAstrocartographyOrdinal(targetResult?.location_score, { rankingEligible });
  const rankStability = getAstrocartographyRankStability(targetResult?.location_score);
  const experimentalMeta = EXPERIMENTAL_GOAL_META[String(selectedGoal?.id || '').toLowerCase()] || null;
  const latitude = Number(target.latitude);
  const longitude = Number(target.longitude);

  return (
    <div className={`${astroSectionCardCls} space-y-3`}>
      <div className={`flex items-start justify-between gap-3 ${astroHeaderDividerCls}`}>
        <div className="min-w-0">
          <ConsoleBracketEyebrow module="astrocartography">selected city</ConsoleBracketEyebrow>
          <div className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">{targetLabel}</div>
          {Number.isFinite(latitude) && Number.isFinite(longitude) ? (
            <div className="mt-1 text-[12px] text-zinc-600 dark:text-zinc-300">
              {latitude.toFixed(4)}, {longitude.toFixed(4)}
            </div>
          ) : null}
        </div>
        <button
          type="button"
          className={actionButtonCls}
          onClick={onAddToCompare}
          disabled={rankingEligible === false}
          title={rankingEligible === false ? 'Birth-time uncertainty makes this chart inspection-only.' : undefined}
        >
          Add To Compare
        </button>
      </div>
      {leadFactor ? (
        <div className={astroBandCls}>
          <div className={astroSectionLabelCls}>Lead factor</div>
          <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">{leadFactor}</p>
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-2 xl:grid-cols-3">
        <MetricChip label="Mode" value={activeMode} tone="default" />
        {selectedGoal?.label ? <MetricChip label="Goal" value={selectedGoal.label} tone="accent" /> : null}
        <MetricChip label="Natal signal" value={getAstrocartographyOrdinal({ score: natalSignal })} tone="default" />
        {viewMode === 'transit' && targetResult?.transit?.reading?.signal_score != null ? (
          <MetricChip label="Transit signal" value={getAstrocartographyOrdinal({ score: transitSignal })} tone="accent" />
        ) : null}
        {targetResult?.location_score?.score != null ? (
          <MetricChip
            label={scoreLabel}
            value={`${scoreOrdinal} · index ${locationScore}${hasScoreInterval ? ` · sampled ${scoreLow}–${scoreHigh}` : ''}`}
            tone={getSignalMetricTone(locationScore, higherIsWorse)}
          />
        ) : null}
        <MetricChip label="Rank stability" value={rankStability.label} tone="default" />
      </div>
      {experimentalMeta ? (
        <div className="rounded-[4px] border border-amber-200 bg-amber-50/80 p-3 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
          <div className={astroSectionLabelCls}>{experimentalMeta.label}</div>
          <p className="mt-2 text-[12px] leading-6">{experimentalMeta.caveat}</p>
        </div>
      ) : null}
      <div className={astroNestedCardCls}>
        <div className={astroSectionLabelCls}>Current scope</div>
        <p className="mt-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
          Scoped to the current body, angle, PathFinder goal, and transit configuration.
        </p>
        {selectedGoal?.transit_strategy === 'ignore' && viewMode === 'transit' ? (
          <p className="mt-2 text-[12px] leading-6 text-amber-700 dark:text-amber-300">
            {selectedGoal.label} currently ignores transit overlay and scores from the natal map only.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function InsightCard({ card }) {
  if (!card) return null;
  return (
    <div className={`rounded-[4px] border p-3 ${getToneCls(card.tone)}`}>
      <div className={astroSectionLabelCls}>{card.title}</div>
      <div className="mt-1 text-sm font-medium text-zinc-900 dark:text-zinc-100">{card.value}</div>
      {card.detail ? <p className="mt-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">{card.detail}</p> : null}
    </div>
  );
}

function ReportSection({ section }) {
  if (!section) return null;
  const items = Array.isArray(section.items) ? section.items : [];
  return (
    <section className={`${astroSectionCardCls} space-y-3`}>
      <div className={`flex items-center justify-between gap-2 ${astroHeaderDividerCls}`}>
        <div>
          <ConsoleBracketEyebrow module="astrocartography">report section</ConsoleBracketEyebrow>
          <h4 className="mt-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">{section.title}</h4>
        </div>
        <span className={astroSectionLabelCls}>{items.length} items</span>
      </div>
      {section.summary ? (
        <div className={astroBandCls}>
          <p className={astroBodyTextCls}>{section.summary}</p>
        </div>
      ) : null}
      {items.length ? (
        <div className="space-y-2">
          {items.map((item, index) => (
            <div key={`${section.id}-${index}`} className={`rounded-[4px] border p-3 ${getToneCls(item.tone)}`}>
              <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{item.title}</div>
              <p className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">{item.body}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className={astroBodyTextCls}>No structured notes available in this section yet.</p>
      )}
    </section>
  );
}

function ReadingLineCard({ row }) {
  if (!row) return null;
  const interpretationStatus = String(row.interpretation_status || '').trim().toLowerCase();
  const interpretationMeta = interpretationStatus === 'curated_experimental_extension'
    ? {
      label: 'Experimental extension',
      detail: 'This Node or Chiron meaning is a separately curated experimental extension.',
      className: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100',
    }
    : interpretationStatus === 'generic_unsupported_fallback'
      ? {
        label: 'Generic fallback',
        detail: 'No dedicated body–angle interpretation is available for this line.',
        className: 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100',
      }
      : interpretationStatus === 'curated_supported_matrix'
        ? {
          label: 'Curated line meaning',
          detail: 'This reading uses the dedicated body–angle interpretation.',
          className: 'border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-100',
        }
        : null;
  return (
    <div className={astroNestedCardCls}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-medium">{row.label}</div>
          <div className="text-xs text-zinc-600 dark:text-zinc-300 mt-1">{row.distance_km} km away</div>
        </div>
        <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getZoneBadgeCls(row.zone)}`}>
          {row.zone}
        </span>
      </div>
      {interpretationMeta ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] ${interpretationMeta.className}`}
            title={interpretationMeta.detail}
          >
            {interpretationMeta.label}
          </span>
          <span className={astroMetaTextCls}>{interpretationMeta.detail}</span>
        </div>
      ) : null}
      <p className="mt-2 text-[12px] leading-6 text-zinc-700 dark:text-zinc-200">{row.summary}</p>
      <p className={`mt-2 ${astroMetaTextCls}`}>{row.caution}</p>
    </div>
  );
}

function ReadingPanel({ title, reading, emptyText, higherIsWorse = false }) {
  const signalScore = Number(reading?.signal_score || 0);
  const signalOrdinal = getAstrocartographyOrdinal({ score: signalScore });
  return (
    <ConsoleRailSection
      title={title}
      eyebrow="reading"
      module="astrocartography"
      headerRight={reading?.signal_score != null ? (
        <span
          className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(signalScore, higherIsWorse)}`}
          title={`Model index ${signalScore}`}
        >
          Signal {signalOrdinal}
        </span>
      ) : null}
      bodyClassName="mt-3 space-y-3"
    >
      {reading ? (
        <>
          <div className={astroBandCls}>
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{reading.headline}</p>
            <p className="mt-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">{reading.support_note}</p>
          </div>
          {Array.isArray(reading.nearest_lines) && reading.nearest_lines.length ? (
            <div className="space-y-2">
              {reading.nearest_lines.slice(0, 4).map((row) => (
                <ReadingLineCard key={row.id} row={row} />
              ))}
            </div>
          ) : null}
        </>
      ) : (
        <p className={astroBodyTextCls}>{emptyText}</p>
      )}
    </ConsoleRailSection>
  );
}

function BirthTimeAssessmentPanel({ assessment, sampling, lineUncertainty }) {
  const meta = assessment || getAstrocartographyBirthTimeAssessment();
  const samplingPayload = sampling && typeof sampling === 'object' ? sampling : {};
  const corridorPayload = lineUncertainty && typeof lineUncertainty === 'object' ? lineUncertainty : {};
  const samplingCount = Number(
    samplingPayload.recomputed_sample_count
    ?? samplingPayload.sample_count
    ?? samplingPayload.samples?.length
    ?? 0
  );
  const sampledMinutes = Number(samplingPayload.sampled_uncertainty_minutes);
  const widestCorridor = Array.isArray(corridorPayload.corridors)
    ? corridorPayload.corridors.reduce((widest, item) => {
      const width = Number(item?.sampled_width_km_at_equator);
      return Number.isFinite(width) ? Math.max(widest, width) : widest;
    }, 0)
    : 0;
  const statusCls = meta.rankingEligible === true
    ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100'
    : (meta.rankingEligible === false
      ? 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100'
      : 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100');
  return (
    <ConsoleRailSection title="Birth-time accuracy" eyebrow="eligibility" module="astrocartography" bodyClassName="mt-3 space-y-2">
      <div className={`rounded-[4px] border p-3 ${statusCls}`}>
        <div className="text-sm font-medium">{meta.accuracyLabel}</div>
        <div className="mt-1 text-[11px] leading-5">
          {[meta.confidenceLabel, meta.uncertaintyLabel].filter(Boolean).join(' · ')}
        </div>
        <div className="mt-2 font-mono text-[10px] font-semibold uppercase tracking-[0.12em]">
          {meta.rankingLabel}
        </div>
      </div>
      {meta.reason ? <p className={astroMetaTextCls}>{meta.reason}</p> : null}
      {meta.warnings?.length ? (
        <ul className="space-y-1 text-[11px] leading-5 text-amber-700 dark:text-amber-200">
          {meta.warnings.slice(0, 3).map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      ) : null}
      {samplingCount > 0 ? (
        <div className={astroNestedCardCls}>
          <div className={astroSectionLabelCls}>Observed time sensitivity</div>
          <p className="mt-2 text-[12px] leading-5 text-zinc-700 dark:text-zinc-200">
            Recalculated {samplingCount} alternative birth times
            {Number.isFinite(sampledMinutes) ? ` across ±${sampledMinutes} minutes` : ''}.
          </p>
          {samplingPayload.assumption ? (
            <p className={`mt-1 ${astroMetaTextCls}`}>{samplingPayload.assumption}</p>
          ) : null}
          {widestCorridor > 0 ? (
            <p className={`mt-1 ${astroMetaTextCls}`}>
              The widest sampled map-line envelope is about {Math.round(widestCorridor)} km at the equator; curved rising and setting lines vary by latitude.
            </p>
          ) : null}
        </div>
      ) : null}
    </ConsoleRailSection>
  );
}

function MethodologyPanel({
  targetResult,
  mapData,
  atlasResults,
  compareResult,
  activeParans,
}) {
  const calculation = firstNonEmptyObject(
    targetResult?.calculation,
    atlasResults?.calculation,
    compareResult?.calculation,
    mapData?.calculation,
  );
  const provenance = firstNonEmptyObject(
    targetResult?.provenance,
    atlasResults?.provenance,
    compareResult?.provenance,
    mapData?.provenance,
  );
  const distancePolicy = firstNonEmptyObject(
    targetResult?.distance_policy,
    atlasResults?.distance_policy,
    compareResult?.distance_policy,
    mapData?.distance_policy,
  );
  const warnings = Array.from(new Set([
    ...(Array.isArray(calculation?.warnings) ? calculation.warnings : []),
    ...(Array.isArray(provenance?.warnings) ? provenance.warnings : []),
    ...(Array.isArray(distancePolicy?.warnings) ? distancePolicy.warnings : []),
    ...(Array.isArray(activeParans?.warnings) ? activeParans.warnings : []),
    ...(Array.isArray(targetResult?.relocation?.warnings) ? targetResult.relocation.warnings : []),
  ].map((item) => String(item || '').trim()).filter(Boolean)));
  const degraded = Boolean(
    calculation?.degraded
    || String(calculation?.status || '').toLowerCase() === 'degraded'
    || provenance?.degraded
    || String(provenance?.status || '').toLowerCase() === 'degraded'
    || mapData?.map?.global_parans?.degraded
    || mapData?.map?.transit_global_parans?.degraded
    || activeParans?.degraded
  );
  const hasMethodMetadata = Boolean(
    Object.keys(calculation || {}).length
    || Object.keys(provenance || {}).length
    || Object.keys(distancePolicy || {}).length
    || Object.keys(activeParans || {}).length
  );
  const scalarPolicyEntries = Object.entries(distancePolicy)
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .slice(0, 8);
  const paranAngleFilter = firstNonEmptyObject(
    activeParans?.angle_filter,
    targetResult?.filters?.policy,
    atlasResults?.filters?.policy,
    compareResult?.filters?.policy,
    mapData?.filters?.policy,
  );
  const effectiveParanAngles = Array.isArray(paranAngleFilter?.effective_angles)
    ? paranAngleFilter.effective_angles
    : [];
  const primaryCalculation = firstNonEmptyObject(
    provenance?.natal,
    calculation?.natal,
    provenance?.transit,
    calculation?.transit,
    provenance,
    calculation,
  );
  const provenanceLabel = String(
    provenance?.label
    || provenance?.source
    || provenance?.engine
    || primaryCalculation?.label
    || primaryCalculation?.source
    || primaryCalculation?.engine
    || calculation?.method
    || calculation?.engine
    || 'Not reported'
  );
  const versionLabel = String(
    provenance?.version
    || calculation?.version
    || primaryCalculation?.version
    || primaryCalculation?.geometry?.version
    || ''
  );
  const frameLabel = String(
    primaryCalculation?.frame
    || primaryCalculation?.geometry?.coordinate_frame
    || ''
  );
  return (
    <ConsoleRailSection
      title="Method / provenance"
      eyebrow="policy"
      module="astrocartography"
      headerRight={(
        <span className={`rounded-full border px-2 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.12em] ${
          degraded
            ? 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200'
            : 'border-zinc-300 bg-zinc-50 text-zinc-600 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200'
        }`}>
          {degraded ? 'Degraded' : (hasMethodMetadata ? 'Reported' : 'Not reported')}
        </span>
      )}
      bodyClassName="mt-3 space-y-2"
    >
      <div className={astroNestedCardCls}>
        <div className={astroSectionLabelCls}>Calculation source</div>
        <p className="mt-2 text-[12px] leading-5 text-zinc-700 dark:text-zinc-200">
          {provenanceLabel}{versionLabel ? ` · ${versionLabel}` : ''}
        </p>
        {frameLabel ? <p className={`mt-1 ${astroMetaTextCls}`}>Frame: {formatStatusLabel(frameLabel)}</p> : null}
      </div>
      <div className={astroNestedCardCls}>
        <div className={astroSectionLabelCls}>Paran policy</div>
        <p className="mt-2 text-[12px] leading-5 text-zinc-600 dark:text-zinc-300">
          {activeParans?.orb_deg != null
            ? `Angular residual limit ≤ ${activeParans.orb_deg}°`
            : (distancePolicy?.local_paran_orb_deg != null
              ? `Local angular residual limit ≤ ${distancePolicy.local_paran_orb_deg}°`
              : 'Angular residual limit not reported')}
          {activeParans?.max_distance_km != null
            ? ` · distance ≤ ${activeParans.max_distance_km} km`
            : (distancePolicy?.local_paran_radius_km != null
              ? ` · local radius ${distancePolicy.local_paran_radius_km} km`
              : '')}
          {distancePolicy?.global_paran_orb_deg != null
            ? ` · global residual limit ≤ ${distancePolicy.global_paran_orb_deg}°`
            : ''}
        </p>
        <p className={`mt-1 ${astroMetaTextCls}`}>
          These orb and distance limits are Vox Stella comparison settings, not universal astronomical boundaries.
        </p>
        {effectiveParanAngles.length ? (
          <p className={`mt-1 ${astroMetaTextCls}`}>
            Both angular events must match: {effectiveParanAngles.join(', ')}
          </p>
        ) : null}
      </div>
      {scalarPolicyEntries.length ? (
        <div className={astroNestedCardCls}>
          <div className={astroSectionLabelCls}>Distance policy</div>
          <div className="mt-2 space-y-1 text-[11px] leading-5 text-zinc-600 dark:text-zinc-300">
            {scalarPolicyEntries.map(([key, value]) => (
              <div key={key}>{formatStatusLabel(key)}: {String(value)}</div>
            ))}
          </div>
        </div>
      ) : (
        <p className={astroMetaTextCls}>Distance thresholds were not reported by this response.</p>
      )}
      {warnings.length ? (
        <div className="rounded-[4px] border border-amber-200 bg-amber-50/80 p-3 text-[11px] leading-5 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
          {warnings.slice(0, 4).map((warning) => <div key={warning}>{warning}</div>)}
        </div>
      ) : null}
    </ConsoleRailSection>
  );
}

function buildRealtimeTransitSeed(seed) {
  return {
    transitDatetime: new Date().toISOString(),
    transitLocation: seed.location || '',
    transitTimezone: seed.timezone || '',
  };
}

function buildManualTransitSeed({ date, time, location, timezone }) {
  if (!date || !time) return null;
  return {
    transitDatetime: `${date}T${time}:00`,
    transitLocation: location || '',
    transitTimezone: timezone || '',
  };
}

function beginAbortableRequest(ref) {
  ref.current.controller?.abort();
  const controller = new AbortController();
  const runId = Number(ref.current.runId || 0) + 1;
  ref.current = { runId, controller };
  return { runId, controller };
}

function abortTrackedRequest(ref) {
  ref.current.controller?.abort();
  ref.current = {
    runId: Number(ref.current.runId || 0) + 1,
    controller: null,
  };
}

function isAbortError(error) {
  return error?.name === 'AbortError' || error?.code === 'ABORT_ERR';
}

export default function AstrocartographyModal({
  open,
  onClose,
  defaultHouseSystem = 'R',
  initialTransitContext = null,
  initialGoalOptions = EMPTY_ITEMS,
  snaps = EMPTY_ITEMS,
  activeSnapId = '',
  onCreateSnap = null,
}) {
  const [snapOptions, setSnapOptions] = useState(Array.isArray(snaps) ? snaps : []);
  const [loadingSnaps, setLoadingSnaps] = useState(false);
  const [creatingSnap, setCreatingSnap] = useState(false);
  const [createSnapError, setCreateSnapError] = useState('');
  const [snapLoadError, setSnapLoadError] = useState('');
  const [goalOptions, setGoalOptions] = useState(() => (
    Array.isArray(initialGoalOptions) && initialGoalOptions.length
      ? filterFrontendGoalOptions(initialGoalOptions)
      : (Array.isArray(astrocartographyGoalOptionsCache) ? astrocartographyGoalOptionsCache : [])
  ));
  const [analysisMode, setAnalysisMode] = useState('astrocartography');
  const [loadingGoals, setLoadingGoals] = useState(false);
  const [goalLoadError, setGoalLoadError] = useState('');
  const [showGoalsLoading, setShowGoalsLoading] = useState(false);
  const [selectedGoalId, setSelectedGoalId] = useState('');
  const [workspaceTab, setWorkspaceTab] = useState('map');
  const [localSpaceMode, setLocalSpaceMode] = useState('relocated');
  const [selectedSnapId, setSelectedSnapId] = useState(() => String(activeSnapId || snaps?.[0]?.id || ''));
  const [viewMode, setViewMode] = useState('natal');
  const [transitMode, setTransitMode] = useState('realtime');
  const [transitDate, setTransitDate] = useState('');
  const [transitTime, setTransitTime] = useState('');
  const [transitLocation, setTransitLocation] = useState('');
  const [transitTimezone, setTransitTimezone] = useState('');
  const [appliedTransitRequest, setAppliedTransitRequest] = useState(null);
  const [selectedBodies, setSelectedBodies] = useState(() => BODY_OPTIONS.map((item) => item.id));
  const [selectedAngles, setSelectedAngles] = useState(() => [...ANGLE_OPTIONS]);
  const [mapData, setMapData] = useState(null);
  const [loadingMap, setLoadingMap] = useState(false);
  const [mapError, setMapError] = useState('');
  const [targetQuery, setTargetQuery] = useState('');
  const [targetResult, setTargetResult] = useState(null);
  const [loadingTarget, setLoadingTarget] = useState(false);
  const [targetError, setTargetError] = useState('');
  const [atlasQuery, setAtlasQuery] = useState('');
  const [atlasCountryCode, setAtlasCountryCode] = useState('');
  const [atlasContinentCode, setAtlasContinentCode] = useState('');
  const [atlasResolution, setAtlasResolution] = useState('standard');
  const [atlasResults, setAtlasResults] = useState(null);
  const [loadingAtlas, setLoadingAtlas] = useState(false);
  const [atlasError, setAtlasError] = useState('');
  const [atlasSessionId, setAtlasSessionId] = useState('');
  const [atlasProgress, setAtlasProgress] = useState(null);
  const [compareTargets, setCompareTargets] = useState([]);
  const [compareResult, setCompareResult] = useState(null);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [compareError, setCompareError] = useState('');
  const [showGlobalParans, setShowGlobalParans] = useState(false);
  const [showAtlasPins, setShowAtlasPins] = useState(true);
  const mountedRef = useRef(true);
  const atlasRunIdRef = useRef(0);
  const atlasAbortControllerRef = useRef(null);
  const atlasSessionIdRef = useRef('');
  const mapRequestRef = useRef({ runId: 0, controller: null });
  const targetRequestRef = useRef({ runId: 0, controller: null });
  const compareRequestRef = useRef({ runId: 0, controller: null });

const actionButtonCls = 'rounded-[3px] border border-zinc-300 bg-white px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-700 shadow-none hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900/45 dark:text-zinc-100 dark:hover:bg-zinc-900/70';
const primaryActionButtonCls = 'rounded-[3px] border border-zinc-900 bg-zinc-900 px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200';
const railCardCls = 'rounded-[4px] border border-zinc-200/90 bg-white/96 dark:border-zinc-700/90 dark:bg-zinc-900/88 backdrop-blur-xl shadow-none';
  const beginAtlasRun = useCallback(() => {
    atlasAbortControllerRef.current?.abort();
    atlasAbortControllerRef.current = new AbortController();
    atlasRunIdRef.current += 1;
    return atlasRunIdRef.current;
  }, []);
  const abortAtlasRun = useCallback(() => {
    atlasAbortControllerRef.current?.abort();
    atlasAbortControllerRef.current = null;
    atlasRunIdRef.current += 1;
  }, []);
  const isAtlasRunActive = useCallback((runId) => (
    mountedRef.current && atlasRunIdRef.current === runId
  ), []);
  const abortFrontendRequests = useCallback(() => {
    abortTrackedRequest(mapRequestRef);
    abortTrackedRequest(targetRequestRef);
    abortTrackedRequest(compareRequestRef);
  }, []);
  const setTrackedAtlasSessionId = useCallback((value) => {
    const sessionId = String(value || '');
    atlasSessionIdRef.current = sessionId;
    setAtlasSessionId(sessionId);
  }, []);
  const cancelAtlasSearchSession = useCallback(async (sessionId) => {
    const nextSessionId = String(sessionId || '').trim();
    if (!nextSessionId) return;
    try {
      await AstroClockAPI.cancelAstrocartographyAtlasSearch(nextSessionId);
    } catch (_) {
    }
  }, []);
  const handleClose = useCallback(() => {
    const activeSessionId = atlasSessionIdRef.current;
    abortAtlasRun();
    abortFrontendRequests();
    setLoadingMap(false);
    setLoadingTarget(false);
    setLoadingAtlas(false);
    setLoadingCompare(false);
    setTrackedAtlasSessionId('');
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
    onClose?.();
  }, [abortAtlasRun, abortFrontendRequests, cancelAtlasSearchSession, onClose, setTrackedAtlasSessionId]);

  useEffect(() => () => {
    const activeSessionId = atlasSessionIdRef.current;
    mountedRef.current = false;
    abortAtlasRun();
    abortFrontendRequests();
    atlasSessionIdRef.current = '';
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [abortAtlasRun, abortFrontendRequests, cancelAtlasSearchSession]);

  useEffect(() => {
    if (open) return;
    const activeSessionId = atlasSessionIdRef.current;
    abortAtlasRun();
    abortFrontendRequests();
    setLoadingMap(false);
    setLoadingTarget(false);
    setLoadingAtlas(false);
    setLoadingCompare(false);
    setTrackedAtlasSessionId('');
    setCreatingSnap(false);
    setCreateSnapError('');
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [abortAtlasRun, abortFrontendRequests, cancelAtlasSearchSession, open, setTrackedAtlasSessionId]);

  useEffect(() => {
    if (!open) return;
    setSnapOptions(Array.isArray(snaps) ? snaps : []);
    setSnapLoadError('');
  }, [open, snaps]);

  useEffect(() => {
    if (!Array.isArray(initialGoalOptions) || !initialGoalOptions.length) return;
    const filteredGoals = filterFrontendGoalOptions(initialGoalOptions);
    astrocartographyGoalOptionsCache = filteredGoals;
    setGoalOptions(filteredGoals);
    setLoadingGoals(false);
    setGoalLoadError('');
  }, [initialGoalOptions]);

  useEffect(() => {
    if (!open) return;
    abortAtlasRun();
    abortFrontendRequests();
    setLoadingMap(false);
    setLoadingTarget(false);
    setLoadingAtlas(false);
    setLoadingCompare(false);
    const seed = initialTransitContext || {};
    setSelectedSnapId(String(activeSnapId || seed.snapId || ''));
    setViewMode('natal');
    setTransitMode('realtime');
    setSelectedGoalId('');
    setWorkspaceTab('map');
    setLocalSpaceMode('relocated');
    setTransitDate(typeof seed.date === 'string' ? seed.date : '');
    setTransitTime(typeof seed.time === 'string' ? seed.time : '');
    setTransitLocation(typeof seed.location === 'string' ? seed.location : '');
    setTransitTimezone(typeof seed.timezone === 'string' ? seed.timezone : '');
    setAppliedTransitRequest(null);
    setMapData(null);
    setMapError('');
    setTargetQuery('');
    setTargetResult(null);
    setTargetError('');
    setAtlasQuery('');
    setAtlasCountryCode('');
    setAtlasContinentCode('');
    setAtlasResolution('standard');
    setAtlasResults(null);
    setAtlasError('');
    setTrackedAtlasSessionId('');
    setAtlasProgress(null);
    setCompareTargets([]);
    setCompareResult(null);
    setCompareError('');
    setCreateSnapError('');
    setSnapLoadError('');
    setGoalLoadError('');
  }, [abortAtlasRun, abortFrontendRequests, open, initialTransitContext, activeSnapId, setTrackedAtlasSessionId]);

  const loadSnaps = useCallback(async () => {
    setLoadingSnaps(true);
    setSnapLoadError('');
    try {
      const res = await AstroClockAPI.listSnaps();
      const items = res?.data?.items || res?.items || res?.data?.snaps || [];
      if (!res?.success || !Array.isArray(items)) {
        throw new Error(res?.error || res?.detail || 'Failed to load saved natal snaps.');
      }
      if (mountedRef.current) {
        setSnapOptions(items);
      }
    } catch (error) {
      if (mountedRef.current) {
        setSnapLoadError(describeAstrocartographyError(error, 'Failed to load saved natal snaps. Refresh to retry.'));
      }
    } finally {
      if (mountedRef.current) {
        setLoadingSnaps(false);
      }
    }
  }, []);

  const loadGoals = useCallback(async () => {
    if (Array.isArray(initialGoalOptions) && initialGoalOptions.length) {
      const filteredGoals = filterFrontendGoalOptions(initialGoalOptions);
      astrocartographyGoalOptionsCache = filteredGoals;
      setGoalOptions(filteredGoals);
      setGoalLoadError('');
      setLoadingGoals(false);
      return filteredGoals;
    }
    if (Array.isArray(astrocartographyGoalOptionsCache)) {
      setGoalOptions(astrocartographyGoalOptionsCache);
      setGoalLoadError('');
      setLoadingGoals(false);
      return astrocartographyGoalOptionsCache;
    }
    setLoadingGoals(true);
    setGoalLoadError('');
    try {
      if (!astrocartographyGoalOptionsPromise) {
        astrocartographyGoalOptionsPromise = AstroClockAPI.listAstrocartographyGoals()
          .then((res) => {
            if (!(res?.success && Array.isArray(res?.data?.goals))) {
              throw new Error(res?.error || res?.detail || 'Failed to load PathFinder goals.');
            }
            const goals = res.data.goals;
            const filteredGoals = filterFrontendGoalOptions(goals);
            astrocartographyGoalOptionsCache = filteredGoals;
            return filteredGoals;
          })
          .finally(() => {
            astrocartographyGoalOptionsPromise = null;
          });
      }
      const goals = await astrocartographyGoalOptionsPromise;
      if (mountedRef.current && Array.isArray(goals)) {
        setGoalOptions(goals);
      }
    } catch (error) {
      if (mountedRef.current) {
        setGoalLoadError(describeAstrocartographyError(error, 'Failed to load PathFinder goals. Refresh to retry.'));
      }
    } finally {
      if (mountedRef.current) setLoadingGoals(false);
    }
  }, [initialGoalOptions]);

  useEffect(() => {
    if (!open || analysisMode !== 'astrocartography') return;
    if (Array.isArray(snaps) && snaps.length) return;
    loadSnaps();
  }, [analysisMode, loadSnaps, open, snaps]);

  useEffect(() => {
    if (!open || analysisMode !== 'astrocartography') return;
    if (Array.isArray(initialGoalOptions) && initialGoalOptions.length) {
      const filteredGoals = filterFrontendGoalOptions(initialGoalOptions);
      astrocartographyGoalOptionsCache = filteredGoals;
      setGoalOptions(filteredGoals);
      return;
    }
    if (Array.isArray(astrocartographyGoalOptionsCache)) {
      setGoalOptions(astrocartographyGoalOptionsCache);
      return;
    }
    loadGoals();
  }, [analysisMode, initialGoalOptions, loadGoals, open]);

  useEffect(() => {
    if (!loadingGoals) {
      setShowGoalsLoading(false);
      return;
    }
    const timerId = setTimeout(() => {
      if (mountedRef.current) setShowGoalsLoading(true);
    }, 150);
    return () => clearTimeout(timerId);
  }, [loadingGoals]);

  useEffect(() => {
    if (!Array.isArray(goalOptions) || !goalOptions.length) return;
    if (!selectedGoalId) return;
    const hasSelectedGoal = goalOptions.some((item) => String(item?.id || '') === String(selectedGoalId || ''));
    if (hasSelectedGoal) return;
    setSelectedGoalId('');
  }, [goalOptions, selectedGoalId]);

  const activeTransitRequest = viewMode === 'transit' ? appliedTransitRequest : null;
  const houseSystem = defaultHouseSystem || 'R';
  const filterSignature = `${selectedBodies.join('|')}::${selectedAngles.join('|')}::${activeTransitRequest ? JSON.stringify(activeTransitRequest) : 'natal'}`;

  const fetchMap = useCallback(async () => {
    if (!selectedSnapId) {
      setMapData(null);
      setMapError('Choose a saved natal snap to load the map.');
      return;
    }
    const selectedSnap = (Array.isArray(snapOptions) ? snapOptions : []).find(
      (snap) => String(snap?.id || '') === String(selectedSnapId),
    );
    if (!isSavedSnapCalculationEligible(selectedSnap)) {
      setMapData(null);
      setMapError(
        'This saved chart needs context review before astrocartography. Correct it in Astro Clock and use the corrected copy.',
      );
      return;
    }
    const { runId, controller } = beginAbortableRequest(mapRequestRef);
    const isActive = () => (
      mountedRef.current
      && mapRequestRef.current.runId === runId
      && !controller.signal.aborted
    );
    setLoadingMap(true);
    setMapError('');
    try {
      const res = await AstroClockAPI.getAstrocartographyMap({
        natalSnapId: selectedSnapId,
        houseSystem,
        bodies: selectedBodies,
        angles: selectedAngles,
        signal: controller.signal,
        ...(activeTransitRequest || {}),
      });
      if (!res?.success) {
        throw new Error('Failed to load astrocartography map.');
      }
      if (isActive()) setMapData(res.data || null);
    } catch (error) {
      if (isAbortError(error) || !isActive()) return;
      setMapData(null);
      setMapError(describeAstrocartographyError(error, 'Failed to load astrocartography map.'));
    } finally {
      if (isActive()) setLoadingMap(false);
    }
  }, [activeTransitRequest, houseSystem, selectedAngles, selectedBodies, selectedSnapId, snapOptions]);

  useEffect(() => {
    if (!open || analysisMode !== 'astrocartography' || !selectedSnapId) return;
    fetchMap();
  }, [analysisMode, fetchMap, open, selectedSnapId]);

  useEffect(() => {
    if (!open) return;
    const activeSessionId = atlasSessionIdRef.current;
    abortAtlasRun();
    abortTrackedRequest(targetRequestRef);
    abortTrackedRequest(compareRequestRef);
    setLoadingTarget(false);
    setLoadingAtlas(false);
    setLoadingCompare(false);
    setTargetResult(null);
    setTargetError('');
    setAtlasResults(null);
    setAtlasError('');
    setTrackedAtlasSessionId('');
    setAtlasProgress(null);
    setCompareTargets([]);
    setCompareResult(null);
    setCompareError('');
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [abortAtlasRun, cancelAtlasSearchSession, filterSignature, open, selectedSnapId, setTrackedAtlasSessionId]);

  const handleApplyTransit = useCallback(() => {
    if (transitMode === 'realtime') {
      setAppliedTransitRequest(buildRealtimeTransitSeed({ location: transitLocation, timezone: transitTimezone }));
      return;
    }
    const next = buildManualTransitSeed({
      date: transitDate,
      time: transitTime,
      location: transitLocation,
      timezone: transitTimezone,
    });
    if (!next) {
      setTargetError('');
      setMapError('Transit mode requires both date and time.');
      return;
    }
    setAppliedTransitRequest(next);
  }, [transitDate, transitLocation, transitMode, transitTime, transitTimezone]);

  const handleInspectTarget = useCallback(async (queryOverride = '') => {
    const isStructuredTarget = (
      queryOverride
      && typeof queryOverride === 'object'
      && (
        (
          Number.isFinite(Number(queryOverride.latitude))
          && Number.isFinite(Number(queryOverride.longitude))
        )
        || Boolean(getTargetCatalogId(queryOverride))
        || Boolean(getAstrocartographyTargetQuery(queryOverride))
      )
    );
    const structuredTarget = isStructuredTarget ? queryOverride : null;
    const nextQuery = structuredTarget
      ? (
        getAstrocartographyTargetQuery(structuredTarget)
        || getTargetDisplayLabel(
          structuredTarget,
          getTargetCatalogId(structuredTarget) ? `Catalog target ${getTargetCatalogId(structuredTarget)}` : 'Selected target'
        )
      )
      : resolveAstrocartographyTargetQuery(queryOverride, targetQuery);
    if (!selectedSnapId) {
      setTargetError('Choose a saved natal snap first.');
      return;
    }
    if (!nextQuery) {
      setTargetError('Enter a city or location to inspect.');
      return;
    }
    const { runId, controller } = beginAbortableRequest(targetRequestRef);
    const isActive = () => (
      mountedRef.current
      && targetRequestRef.current.runId === runId
      && !controller.signal.aborted
    );
    setLoadingTarget(true);
    setTargetError('');
    try {
      const res = await AstroClockAPI.getAstrocartographyLocation({
        natalSnapId: selectedSnapId,
        houseSystem,
        goalId: selectedGoalId,
        bodies: selectedBodies,
        angles: selectedAngles,
        targetLocation: nextQuery,
        target: structuredTarget,
        signal: controller.signal,
        ...(activeTransitRequest || {}),
      });
      if (!res?.success) {
        throw new Error('Failed to inspect location.');
      }
      if (isActive()) {
        setTargetResult(res.data || null);
        setTargetQuery(nextQuery);
      }
    } catch (error) {
      if (isAbortError(error) || !isActive()) return;
      setTargetResult(null);
      setTargetError(describeAstrocartographyError(error, 'Failed to inspect location.'));
    } finally {
      if (isActive()) setLoadingTarget(false);
    }
  }, [activeTransitRequest, houseSystem, selectedAngles, selectedBodies, selectedGoalId, selectedSnapId, targetQuery]);

  const handleCreateSnap = useCallback(async () => {
    if (typeof onCreateSnap !== 'function') return;
    setCreatingSnap(true);
    setCreateSnapError('');
    try {
      const result = await onCreateSnap();
      if (!result?.success) {
        throw new Error(result?.error || 'Failed to save the current chart as a natal snap.');
      }
      await loadSnaps();
      const createdSnapId = String(result?.id || '');
      if (createdSnapId) {
        setSelectedSnapId(createdSnapId);
      }
    } catch (error) {
      setCreateSnapError(error?.message || 'Failed to save the current chart as a natal snap.');
    } finally {
      setCreatingSnap(false);
    }
  }, [loadSnaps, onCreateSnap]);

  const handleToggleBody = useCallback((bodyId) => {
    setSelectedBodies((prev) => {
      const next = prev.includes(bodyId) ? prev.filter((item) => item !== bodyId) : [...prev, bodyId];
      return next.length ? next : prev;
    });
  }, []);

  const handleToggleAngle = useCallback((angleId) => {
    setSelectedAngles((prev) => {
      const next = prev.includes(angleId) ? prev.filter((item) => item !== angleId) : [...prev, angleId];
      return next.length ? next : prev;
    });
  }, []);

  const addTargetToCompare = useCallback((payload) => {
    if (!payload?.target) return;
    const catalogId = getTargetCatalogId(payload.target)
      || getTargetCatalogId(payload?.atlas_city);
    const displayLabel = getTargetDisplayLabel(payload.target);
    const normalizedTarget = {
      ...payload.target,
      ...(catalogId ? { candidate_id: catalogId } : {}),
      label: displayLabel,
      query: getAstrocartographyTargetQuery(payload.target) || displayLabel,
    };
    const compareKey = buildCompareKey(normalizedTarget);
    const nextEntry = {
      ...payload,
      target: normalizedTarget,
      compareKey,
      addedAt: new Date().toISOString(),
    };
    setCompareTargets((prev) => {
      const filtered = prev.filter((entry) => entry.compareKey !== compareKey);
      return [nextEntry, ...filtered].slice(0, 5);
    });
  }, []);

  const handleAddToCompare = useCallback(() => {
    addTargetToCompare(targetResult);
  }, [addTargetToCompare, targetResult]);

  const handleRemoveCompare = useCallback((compareKey) => {
    setCompareTargets((prev) => prev.filter((entry) => entry.compareKey !== compareKey));
  }, []);

  const handleSearchAtlas = useCallback(async () => {
    if (!selectedGoalId) {
      setAtlasError('Choose a PathFinder goal before running atlas search.');
      return;
    }
    if (!selectedSnapId) {
      setAtlasError('Choose a saved natal snap first.');
      return;
    }
    const selectedSnap = (Array.isArray(snapOptions) ? snapOptions : [])
      .find((item) => String(item?.id || '') === String(selectedSnapId || ''));
    const birthTimeAssessment = getAstrocartographyBirthTimeAssessment(
      mapData,
      targetResult,
      selectedSnap,
    );
    if (birthTimeAssessment.rankingEligible === false) {
      setAtlasError('This chart is inspection-only because its reported birth-time uncertainty is not eligible for ranking.');
      return;
    }
    const runId = beginAtlasRun();
    const controller = atlasAbortControllerRef.current;
    setLoadingAtlas(true);
    setAtlasError('');
    setAtlasResults(null);
    setTrackedAtlasSessionId('');
    setAtlasProgress({
      ready: false,
      failed: false,
      percent: 0,
      stage: 'queued',
      message: 'Atlas search queued',
      done: 0,
      total: 0,
    });
    try {
      const start = await AstroClockAPI.startAstrocartographyAtlasSearch({
        natalSnapId: selectedSnapId,
        houseSystem,
        goalId: selectedGoalId,
        query: atlasQuery,
        countryCode: atlasCountryCode,
        continentCode: atlasContinentCode,
        resolution: atlasResolution,
        limit: 8,
        bodies: selectedBodies,
        angles: selectedAngles,
        signal: controller?.signal,
        ...(activeTransitRequest || {}),
      });
      const sessionId = String(start?.data?.session_id || '');
      if (!sessionId) {
        throw new Error('Failed to start atlas search.');
      }
      if (!isAtlasRunActive(runId)) {
        void cancelAtlasSearchSession(sessionId);
        return;
      }
      setTrackedAtlasSessionId(sessionId);
      const initialProgress = start?.data?.progress || {};
      setAtlasProgress(initialProgress);

      const readyProgress = initialProgress?.ready
        ? initialProgress
        : await pollAsyncSession({
          fetchProgress: async () => {
            const progressRes = await AstroClockAPI.getAstrocartographyAtlasSearchProgress(sessionId, {
              signal: controller?.signal,
            });
            return progressRes?.data || {};
          },
          onProgress: (nextProgress) => {
            if (isAtlasRunActive(runId)) {
              setAtlasProgress(nextProgress);
            }
          },
          shouldContinue: () => isAtlasRunActive(runId),
          delayMs: 450,
          timeoutMs: 20 * 60 * 1000,
          timeoutMessage: 'Atlas search took too long to finish.',
          cancelMessage: 'Atlas search cancelled.',
        });
      if (!isAtlasRunActive(runId)) return;
      setAtlasProgress(readyProgress);

      const resultRes = await AstroClockAPI.getAstrocartographyAtlasSearchResult(sessionId, {
        signal: controller?.signal,
      });
      if (!isAtlasRunActive(runId)) return;
      if (resultRes?.data?.failed) {
        throw new Error(resultRes.data.error || 'Atlas search failed.');
      }
      if (!resultRes?.data?.ready || !resultRes?.data?.result) {
        throw new Error('Atlas search did not return a final result.');
      }
      setAtlasResults(resultRes.data.result || null);
    } catch (error) {
      if (isAbortError(error) || !isAtlasRunActive(runId)) return;
      setAtlasResults(null);
      setAtlasError(describeAstrocartographyError(error, 'Failed to search atlas candidates.'));
    } finally {
      if (isAtlasRunActive(runId)) {
        setLoadingAtlas(false);
        if (atlasAbortControllerRef.current === controller) {
          atlasAbortControllerRef.current = null;
        }
      }
    }
  }, [activeTransitRequest, atlasContinentCode, atlasCountryCode, atlasQuery, atlasResolution, beginAtlasRun, cancelAtlasSearchSession, houseSystem, isAtlasRunActive, mapData, selectedAngles, selectedBodies, selectedGoalId, selectedSnapId, setTrackedAtlasSessionId, snapOptions, targetResult]);

  const natalLines = mapData?.map?.natal_lines || [];
  const transitLines = mapData?.map?.transit_lines || [];
  const globalParanTracks = dedupeCanonicalEvidence(
    Array.isArray(mapData?.map?.global_parans?.tracks) ? mapData.map.global_parans.tracks : []
  );
  const transitGlobalParanTracks = dedupeCanonicalEvidence(
    Array.isArray(mapData?.map?.transit_global_parans?.tracks) ? mapData.map.transit_global_parans.tracks : []
  );
  const selectedTarget = targetResult?.target || null;
  const hasSavedSnaps = Array.isArray(snapOptions) && snapOptions.length > 0;
  const eligibleSnapOptions = useMemo(
    () => (Array.isArray(snapOptions)
      ? snapOptions.filter((snap) => isSavedSnapCalculationEligible(snap))
      : []),
    [snapOptions],
  );
  const selectedSnapNeedsReview = useMemo(
    () => (Array.isArray(snapOptions) ? snapOptions : []).some(
      (snap) => (
        String(snap?.id || '') === String(selectedSnapId || '')
        && !isSavedSnapCalculationEligible(snap)
      ),
    ),
    [selectedSnapId, snapOptions],
  );

  useEffect(() => {
    if (!open || selectedSnapId || !eligibleSnapOptions.length) return;
    const activeEligible = eligibleSnapOptions.find(
      (snap) => String(snap?.id || '') === String(activeSnapId || ''),
    );
    const defaultSnapId = String(activeEligible?.id || eligibleSnapOptions[0]?.id || '');
    if (defaultSnapId) {
      setSelectedSnapId(defaultSnapId);
    }
  }, [activeSnapId, eligibleSnapOptions, open, selectedSnapId]);

  useEffect(() => {
    if (!open || !selectedSnapNeedsReview) return;
    setSelectedSnapId('');
    setSnapLoadError(
      'This saved chart cannot be used for astrocartography. Correct its context or choose its corrected copy in Astro Clock.',
    );
  }, [open, selectedSnapNeedsReview]);

  const snapSummary = useMemo(() => {
    const all = Array.isArray(snapOptions) ? snapOptions : [];
    return all.find((item) => String(item?.id || '') === String(selectedSnapId || '')) || null;
  }, [selectedSnapId, snapOptions]);

  const selectedGoal = useMemo(() => {
    const all = Array.isArray(goalOptions) ? goalOptions : [];
    return all.find((item) => String(item?.id || '') === String(selectedGoalId || '')) || null;
  }, [goalOptions, selectedGoalId]);
  const groupedGoalOptions = useMemo(() => {
    const all = Array.isArray(goalOptions) ? goalOptions : [];
    const groups = [
      { id: 'broad', label: GOAL_GROUP_LABELS.broad, items: [] },
      { id: 'specialist', label: GOAL_GROUP_LABELS.specialist, items: [] },
    ];
    all.forEach((goal) => {
      const tier = getGoalVariantTier(goal);
      const bucket = groups.find((group) => group.id === tier);
      if (bucket) bucket.items.push(goal);
    });
    return groups.filter((group) => group.items.length > 0);
  }, [goalOptions]);
  const selectedGoalTier = selectedGoal ? getGoalVariantTier(selectedGoal) : '';
  const selectedGoalTierLabel = selectedGoalTier ? GOAL_GROUP_LABELS[selectedGoalTier] : '';
  const selectedGoalFamilyLabel = selectedGoal?.goal_family ? formatGoalFamilyLabel(selectedGoal.goal_family) : '';
  const selectedGoalHigherIsWorse = selectedGoal?.score_polarity === 'higher_is_worse';
  const selectedGoalExperimentalMeta = EXPERIMENTAL_GOAL_META[String(selectedGoal?.id || '').toLowerCase()] || null;
  const atlasPinsLabel = selectedGoalHigherIsWorse ? 'Lower-pressure candidates' : 'Ranked candidates';
  const atlasSearchLabel = selectedGoalHigherIsWorse ? 'Rank Lower Pressure' : 'Rank Candidate Cities';
  const atlasScoreLabel = selectedGoalHigherIsWorse ? 'Modeled pressure' : 'Model signal';
  const birthTimeAssessment = useMemo(() => getAstrocartographyBirthTimeAssessment(
    targetResult,
    atlasResults,
    compareResult,
    mapData,
    snapSummary,
  ), [atlasResults, compareResult, mapData, snapSummary, targetResult]);
  const birthTimeSampling = firstNonEmptyObject(
    targetResult?.birth_time_sampling,
    targetResult?.location_score?.uncertainty?.birth_time_sampling,
    atlasResults?.birth_time_sampling,
    atlasResults?.atlas?.birth_time_sampling,
    compareResult?.birth_time_sampling,
    mapData?.birth_time_sampling,
  );
  const natalLineUncertainty = firstNonEmptyObject(
    targetResult?.natal?.line_uncertainty,
    mapData?.map?.natal_line_uncertainty,
  );
  const rankingIneligible = birthTimeAssessment.rankingEligible === false;
  const rankingEligibilityPending = loadingMap && birthTimeAssessment.rankingEligible == null;

  const selectedAtlasResolution = useMemo(() => {
    return ATLAS_RESOLUTION_OPTIONS.find((item) => item.id === atlasResolution) || ATLAS_RESOLUTION_OPTIONS[1];
  }, [atlasResolution]);
  const selectedAtlasContinent = useMemo(() => {
    return ATLAS_CONTINENT_OPTIONS.find((item) => item.id === atlasContinentCode) || ATLAS_CONTINENT_OPTIONS[0];
  }, [atlasContinentCode]);
  const activeTargetMode = viewMode === 'transit' && targetResult?.transit ? 'transit' : 'natal';
  const activeReading = activeTargetMode === 'transit' ? targetResult?.transit?.reading || null : targetResult?.natal?.reading || null;
  const activeIntersections = activeTargetMode === 'transit'
    ? targetResult?.transit?.intersections || targetResult?.natal?.intersections || null
    : targetResult?.natal?.intersections || null;
  const activeParans = activeTargetMode === 'transit'
    ? targetResult?.transit?.parans || targetResult?.natal?.parans || null
    : targetResult?.natal?.parans || null;
  const natalLocalSpace = targetResult?.natal?.local_space || null;
  const relocatedLocalSpace = targetResult?.relocation?.local_space || null;
  const activeLocalSpace = localSpaceMode === 'natal' ? natalLocalSpace : relocatedLocalSpace;
  const relocationHouseSystemCode = String(
    targetResult?.relocation?.provenance?.house_system_code
    || targetResult?.relocation?.meta?.house_system_code
    || targetResult?.relocation?.chart_data?.house_system_code
    || defaultHouseSystem
    || ''
  ).trim().toUpperCase();
  const relocationHouseSystemLabel = HOUSE_SYSTEM_LABELS[relocationHouseSystemCode] || relocationHouseSystemCode;
  const activeLocalSpaceOrigin = getLocalSpaceOrigin(
    activeLocalSpace,
    localSpaceMode === 'relocated' ? selectedTarget : null,
  );
  const reportPayload = targetResult?.report || null;

  const compareEntries = compareTargets;
  const selectedTargetLabel = selectedTarget ? getTargetDisplayLabel(selectedTarget, '') : '';
  const mapTopStatus = [
    { id: 'natal-lines', label: `Natal ${natalLines.length}` },
    viewMode === 'transit' ? { id: 'transit-lines', label: `Transit ${transitLines.length}` } : null,
    showGlobalParans ? { id: 'global-parans', label: `Parans ${globalParanTracks.length + transitGlobalParanTracks.length}` } : null,
    atlasResults?.atlas?.used_live_augmentation ? { id: 'live-aug', label: 'Live Match Expansion', tone: 'accent' } : null,
  ].filter(Boolean);
  const mapBottomStatus = [
    mapData?.natal?.timestamp ? { id: 'natal-time', label: `Natal ${formatCompactTimestamp(mapData.natal.timestamp, mapData.natal.timezone)}` } : null,
    mapData?.transit?.timestamp ? { id: 'transit-time', label: `Transit ${formatCompactTimestamp(mapData.transit.timestamp, mapData.transit.timezone)}` } : null,
    selectedGoal?.label ? { id: 'goal', label: selectedGoal.label, tone: 'accent' } : null,
    selectedTargetLabel ? { id: 'target', label: selectedTargetLabel, tone: 'success' } : null,
  ].filter(Boolean);
  const showInspectorDetails = Boolean(selectedTarget);
  const showAtlasSummary = loadingAtlas || Array.isArray(atlasResults?.results) || atlasResults?.atlas?.candidate_count > 0;
  const showCompareSummary = compareEntries.length > 0 || loadingCompare || Boolean(compareError) || Boolean(compareResult?.ranking?.length);
  const showSnapPreflight = analysisMode === 'astrocartography' && !selectedSnapId;

  const fetchCompare = useCallback(async () => {
    if (!selectedGoalId || !selectedSnapId || compareTargets.length < 2) {
      abortTrackedRequest(compareRequestRef);
      setCompareResult(null);
      setCompareError('');
      setLoadingCompare(false);
      return;
    }
    if (rankingIneligible) {
      abortTrackedRequest(compareRequestRef);
      setCompareResult(null);
      setCompareError('Birth-time uncertainty makes this chart inspection-only; ranked comparison is unavailable.');
      setLoadingCompare(false);
      return;
    }
    const { runId, controller } = beginAbortableRequest(compareRequestRef);
    const isActive = () => (
      mountedRef.current
      && compareRequestRef.current.runId === runId
      && !controller.signal.aborted
    );
    setLoadingCompare(true);
    setCompareError('');
    try {
      const targets = compareTargets
        .map((entry) => entry?.target)
        .filter(Boolean);
      const res = await AstroClockAPI.compareAstrocartographyTargets({
        natalSnapId: selectedSnapId,
        houseSystem,
        goalId: selectedGoalId,
        bodies: selectedBodies,
        angles: selectedAngles,
        targets,
        signal: controller.signal,
        ...(activeTransitRequest || {}),
      });
      if (!res?.success) {
        throw new Error('Failed to compare locations.');
      }
      if (isActive()) setCompareResult(res.data || null);
    } catch (error) {
      if (isAbortError(error) || !isActive()) return;
      setCompareResult(null);
      setCompareError(describeAstrocartographyError(error, 'Failed to compare locations.'));
    } finally {
      if (isActive()) setLoadingCompare(false);
    }
  }, [activeTransitRequest, compareTargets, houseSystem, rankingIneligible, selectedAngles, selectedBodies, selectedGoalId, selectedSnapId]);

  useEffect(() => {
    if (!open || analysisMode !== 'astrocartography') return;
    if (!selectedGoalId || compareTargets.length < 2) {
      abortTrackedRequest(compareRequestRef);
      setCompareResult(null);
      setCompareError('');
      setLoadingCompare(false);
      return;
    }
    fetchCompare();
  }, [analysisMode, compareTargets, fetchCompare, open, selectedGoalId]);

  useEffect(() => {
    if (!open) return;
    abortTrackedRequest(targetRequestRef);
    abortTrackedRequest(compareRequestRef);
    setLoadingTarget(false);
    setLoadingCompare(false);
    setTargetResult(null);
    setTargetError('');
    setCompareTargets([]);
    setCompareResult(null);
    setCompareError('');
  }, [open, selectedGoalId]);

  useEffect(() => {
    if (!open) return;
    const activeSessionId = atlasSessionIdRef.current;
    abortAtlasRun();
    setLoadingAtlas(false);
    setAtlasResults(null);
    setAtlasError('');
    setTrackedAtlasSessionId('');
    setAtlasProgress(null);
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [abortAtlasRun, atlasResolution, cancelAtlasSearchSession, open, selectedGoalId, setTrackedAtlasSessionId]);

  useEffect(() => {
    if (!open || analysisMode === 'astrocartography') return;
    const activeSessionId = atlasSessionIdRef.current;
    abortAtlasRun();
    abortFrontendRequests();
    setLoadingMap(false);
    setLoadingTarget(false);
    setLoadingAtlas(false);
    setLoadingCompare(false);
    setAtlasResults(null);
    setAtlasError('');
    setTrackedAtlasSessionId('');
    setAtlasProgress(null);
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [abortAtlasRun, abortFrontendRequests, analysisMode, cancelAtlasSearchSession, open, setTrackedAtlasSessionId]);

  const activeIntersectionPoints = dedupeCanonicalEvidence(
    Array.isArray(activeIntersections?.geometry_points) ? activeIntersections.geometry_points : []
  );
  const activeParanItems = dedupeCanonicalEvidence(
    Array.isArray(activeParans?.items) ? activeParans.items : []
  );
  const activeParanPoints = activeParanItems.filter((item) => item?.point);
  const activePrimaryCrossings = dedupeCanonicalEvidence(
    Array.isArray(activeIntersections?.primary_crossings) ? activeIntersections.primary_crossings : []
  );
  const reportCards = Array.isArray(reportPayload?.cards) ? reportPayload.cards : [];
  const reportSections = Array.isArray(reportPayload?.sections) ? reportPayload.sections : [];
  const activeLocalSpaceRays = Array.isArray(activeLocalSpace?.rays) ? activeLocalSpace.rays : [];
  const atlasMapPoints = Array.isArray(atlasResults?.results) ? atlasResults.results.slice(0, 8) : [];

  let workspacePanel = (
    <section className={`p-3 ${railCardCls} flex flex-col gap-3`}>
      <WorkspaceHeader
        eyebrow="Workspace"
        title="Map"
        metrics={[
          { label: 'Mode', value: viewMode === 'transit' ? 'Transit' : 'Natal' },
          selectedGoal?.label ? { label: 'Goal', value: selectedGoal.label, tone: 'accent' } : null,
          selectedTargetLabel ? { label: 'City', value: selectedTargetLabel, tone: 'success' } : null,
        ]}
      />
      <div className={`${astroBandCls} flex flex-wrap items-center justify-between gap-3 text-[11px] text-zinc-600 dark:text-zinc-300`}>
        <div className="flex flex-wrap items-center gap-3">
          <span className={astroSectionLabelCls}>Map tools</span>
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" checked={showGlobalParans} onChange={() => setShowGlobalParans((value) => !value)} />
            <span>Global parans</span>
          </label>
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" checked={showAtlasPins} onChange={() => setShowAtlasPins((value) => !value)} />
            <span>{atlasPinsLabel}</span>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {selectedGoal?.label ? <MapHudPill tone="accent">{selectedGoal.label}</MapHudPill> : null}
          {selectedTargetLabel ? <MapHudPill tone="success">Inspecting</MapHudPill> : null}
        </div>
      </div>
      <div className="relative min-h-[34rem] h-[68vh] overflow-hidden rounded-[4px] border border-zinc-200 dark:border-zinc-700" style={{ background: MAP_THEME.water }}>
        <MapContainer
          center={DEFAULT_VIEW.center}
          zoom={DEFAULT_VIEW.zoom}
          style={{ height: '100%', width: '100%', background: MAP_THEME.water }}
          scrollWheelZoom
          attributionControl={false}
          maxBounds={WORLD_BOUNDS}
          maxBoundsViscosity={1}
          minZoom={1.5}
          worldCopyJump={false}
        >
          <NeutralWorldBaseMap />
          <MapViewport target={selectedTarget} />
          <DynamicLineLabels lines={natalLines} placement="north" variant="natal" />
          {viewMode === 'transit' && transitLines.length ? (
            <DynamicLineLabels lines={transitLines} placement="south" variant="transit" />
          ) : null}
          {natalLines.flatMap((line) => (
            (line.segments || []).map((segment, idx) => (
              <Polyline
                key={`natal-${line.id}-${idx}`}
                positions={segment}
                pathOptions={{ color: line.color || '#64748b', weight: 2, opacity: 0.9, dashArray: line.dash_array || undefined }}
              />
            ))
          ))}
          {transitLines.flatMap((line) => (
            (line.segments || []).map((segment, idx) => (
              <Polyline
                key={`transit-${line.id}-${idx}`}
                positions={segment}
                pathOptions={{ color: line.color || '#94a3b8', weight: 2, opacity: 0.55, dashArray: '4 8' }}
              />
            ))
          ))}
          {showGlobalParans && globalParanTracks.flatMap((track) => (
            (track.segments || []).map((segment, idx) => (
              <Polyline
                key={`global-paran-${track.id}-${idx}`}
                positions={segment}
                pathOptions={{ color: track.color || '#7c3aed', weight: 1.6, opacity: 0.55, dashArray: track.dash_array || '3 8' }}
              />
            ))
          ))}
          {showGlobalParans && transitGlobalParanTracks.flatMap((track) => (
            (track.segments || []).map((segment, idx) => (
              <Polyline
                key={`transit-global-paran-${track.id}-${idx}`}
                positions={segment}
                pathOptions={{ color: track.color || '#a78bfa', weight: 1.4, opacity: 0.32, dashArray: '2 10' }}
              />
            ))
          ))}
          {showAtlasPins && atlasMapPoints.map((item, index) => {
            const target = item?.target || {};
            const targetLabel = getTargetDisplayLabel(target, `Candidate ${index + 1}`);
            const score = Number(item?.location_score?.score || 0);
            const scoreColors = getMapScoreColors(score, selectedGoalHigherIsWorse);
            const ordinal = getAstrocartographyOrdinal(item?.location_score, {
              rankingEligible: birthTimeAssessment.rankingEligible,
            });
            if (typeof target.latitude !== 'number' || typeof target.longitude !== 'number') return null;
            return (
              <CircleMarker
                key={`atlas-pin-${getTargetCatalogId(target) || targetLabel || index}`}
                center={[target.latitude, target.longitude]}
                radius={Math.max(4, 8 - index)}
                pathOptions={{ ...scoreColors, weight: 2, fillOpacity: 0.55 }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-medium">{targetLabel}</div>
                    <div>Rank {index + 1} | {atlasScoreLabel}: {ordinal}</div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
          <TargetPin target={selectedTarget} />
        </MapContainer>
        {mapTopStatus.length ? (
          <div className="pointer-events-none absolute left-3 right-3 top-3 flex flex-wrap items-start gap-2">
            {mapTopStatus.map((item) => (
              <MapHudPill key={item.id} tone={item.tone || 'default'}>{item.label}</MapHudPill>
            ))}
          </div>
        ) : null}
        {mapBottomStatus.length ? (
          <div className="pointer-events-none absolute bottom-3 left-3 right-3 flex flex-wrap items-end gap-2">
            {mapBottomStatus.map((item) => (
              <MapHudPill key={item.id} tone={item.tone || 'muted'}>{item.label}</MapHudPill>
            ))}
          </div>
        ) : null}
        {mapError ? (
          <div className="absolute bottom-3 right-3 max-w-[22rem] rounded-[4px] border border-red-200 bg-white/92 px-3 py-2 text-xs text-red-600 dark:border-red-900/50 dark:bg-zinc-900/90">
            {mapError}
          </div>
        ) : null}
      </div>
    </section>
  );

  if (workspaceTab === 'intersections') {
    workspacePanel = (
      <section className={`p-3 ${railCardCls} space-y-3`}>
        {selectedTarget ? (
          <>
            <WorkspaceHeader
              eyebrow="Workspace"
              title="Intersections"
              metrics={[
                { label: 'Intersections', value: activeIntersections?.exact_count || 0, tone: 'warning' },
                { label: 'Parans', value: activeParans?.count || 0, tone: 'accent' },
                { label: 'Mode', value: activeTargetMode === 'transit' ? 'Transit' : 'Natal' },
              ]}
            />
            <div className="relative h-[70vh] overflow-hidden rounded-[4px] border border-zinc-200 dark:border-zinc-700" style={{ background: MAP_THEME.water }}>
              <MapContainer
                center={[selectedTarget.latitude, selectedTarget.longitude]}
                zoom={4}
                style={{ height: '100%', width: '100%', background: MAP_THEME.water }}
                scrollWheelZoom
                attributionControl={false}
                maxBounds={WORLD_BOUNDS}
                maxBoundsViscosity={1}
                minZoom={2}
                worldCopyJump={false}
              >
                <NeutralWorldBaseMap />
                <MapViewport target={selectedTarget} />
                <DynamicLineLabels lines={natalLines} placement="north" variant="natal" />
                {viewMode === 'transit' && transitLines.length ? (
                  <DynamicLineLabels lines={transitLines} placement="south" variant="transit" />
                ) : null}
                {natalLines.flatMap((line) => (
                  (line.segments || []).map((segment, idx) => (
                    <Polyline
                      key={`intersection-natal-${line.id}-${idx}`}
                      positions={segment}
                      pathOptions={{ color: line.color || '#64748b', weight: 1.4, opacity: 0.55, dashArray: line.dash_array || undefined }}
                    />
                  ))
                ))}
                {transitLines.flatMap((line) => (
                  (line.segments || []).map((segment, idx) => (
                    <Polyline
                      key={`intersection-transit-${line.id}-${idx}`}
                      positions={segment}
                      pathOptions={{ color: line.color || '#94a3b8', weight: 1.2, opacity: 0.3, dashArray: '4 8' }}
                    />
                  ))
                ))}
                {activeIntersectionPoints.map((item) => (
                  item.point ? (
                    <CircleMarker
                      key={`${item.canonical_event_id || item.id}-${item.event_kind || 'intersection'}`}
                      center={item.point}
                      radius={6}
                      pathOptions={{ color: '#f59e0b', weight: 2, fillOpacity: 0.75 }}
                    >
                      <Popup>
                        <div className="text-sm">
                          <div className="font-medium">{item.label}</div>
                          <div>{item.distance_km} km away</div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  ) : null
                ))}
                {activeParanPoints.map((item) => (
                  item.point ? (
                    <CircleMarker
                      key={`${item.canonical_event_id || item.id}-${item.event_kind || 'paran'}`}
                      center={item.point}
                      radius={5}
                      pathOptions={{ color: '#7c3aed', weight: 2, fillOpacity: 0.75 }}
                    >
                      <Popup>
                        <div className="text-sm">
                          <div className="font-medium">{item.label}</div>
                          <div>{item.distance_km} km away | orb {item.orb_deg} deg</div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  ) : null
                ))}
                <TargetPin target={selectedTarget} />
              </MapContainer>
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-zinc-600 dark:text-zinc-300">
              <span>Exact intersections: {activeIntersections?.exact_count || 0}</span>
              <span>Blend candidates: {activeIntersections?.blend_count || 0}</span>
              <span>Parans: {activeParans?.count || 0}</span>
              <span>Mode: {activeTargetMode}</span>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-zinc-600 dark:text-zinc-300">{activeIntersections?.headline || 'No nearby intersection geometry yet.'}</p>
              <p className="text-sm text-zinc-600 dark:text-zinc-300">{activeParans?.headline || 'No nearby parans yet.'}</p>
            </div>
          </>
        ) : (
          <WorkspaceEmptyState
            title="Inspect a city to open Intersections."
          />
        )}
      </section>
    );
  } else if (workspaceTab === 'local-space') {
    workspacePanel = (
      <section className={`p-3 ${railCardCls} space-y-3`}>
        {selectedTarget ? (
          <>
            <WorkspaceHeader
              eyebrow="Workspace"
              title={`${localSpaceMode === 'natal' ? 'Natal' : 'Relocated'} Local Space`}
              description={localSpaceMode === 'natal'
                ? 'Directions originate at the recorded birthplace.'
                : 'Directions are recalculated from the inspected location.'}
              metrics={[
                { label: 'Visible', value: activeLocalSpace?.visible_count || 0, tone: 'success' },
                { label: 'Hidden', value: activeLocalSpace?.hidden_count || 0 },
                { label: 'Sectors', value: activeLocalSpace?.dominant_sectors?.length || 0, tone: 'accent' },
              ]}
            />
            <div className={`${astroBandCls} flex flex-wrap items-center justify-between gap-3`}>
              <div>
                <div className={astroSectionLabelCls}>Origin</div>
                <p className="mt-1 text-[12px] text-zinc-600 dark:text-zinc-300">
                  {activeLocalSpaceOrigin ? getTargetDisplayLabel(activeLocalSpaceOrigin, 'Coordinates') : 'Unavailable'}
                </p>
              </div>
              <ConsoleModeTabs options={LOCAL_SPACE_OPTIONS} value={localSpaceMode} onChange={setLocalSpaceMode} />
            </div>
            {activeLocalSpace && activeLocalSpaceOrigin ? (
              <div className="relative h-[70vh] overflow-hidden rounded-[4px] border border-zinc-200 dark:border-zinc-700" style={{ background: MAP_THEME.water }}>
                <MapContainer
                  center={[activeLocalSpaceOrigin.latitude, activeLocalSpaceOrigin.longitude]}
                  zoom={4}
                  style={{ height: '100%', width: '100%', background: MAP_THEME.water }}
                  scrollWheelZoom
                  attributionControl={false}
                  maxBounds={WORLD_BOUNDS}
                  maxBoundsViscosity={1}
                  minZoom={2}
                  worldCopyJump={false}
                >
                  <NeutralWorldBaseMap />
                  <MapViewport target={activeLocalSpaceOrigin} />
                  {(activeLocalSpace?.range_rings_km || []).map((radiusKm) => (
                    <Circle
                      key={`local-space-${localSpaceMode}-ring-${radiusKm}`}
                      center={[activeLocalSpaceOrigin.latitude, activeLocalSpaceOrigin.longitude]}
                      radius={Number(radiusKm) * 1000}
                      pathOptions={{ color: '#94a3b8', weight: 1, opacity: 0.3, dashArray: '4 10' }}
                    />
                  ))}
                  {activeLocalSpaceRays.map((ray) => (
                    (ray.segments || []).map((segment, idx) => (
                      <Polyline
                        key={`local-space-${localSpaceMode}-${ray.id}-${idx}`}
                        positions={segment}
                        pathOptions={{ color: ray.color || '#64748b', weight: 2.2, opacity: ray.above_horizon ? 0.92 : 0.35, dashArray: ray.above_horizon ? undefined : '6 8' }}
                      />
                    ))
                  ))}
                  <TargetPin target={activeLocalSpaceOrigin} />
                </MapContainer>
              </div>
            ) : (
              <WorkspaceEmptyState
                title={`${localSpaceMode === 'natal' ? 'Natal' : 'Relocated'} Local Space is unavailable for this calculation.`}
                detail={localSpaceMode === 'relocated'
                  ? formatServiceError(
                    targetResult?.relocation?.error || targetResult?.relocation?.warnings?.[0],
                    'The service did not return a relocated Local Space calculation.'
                  )
                  : 'The service did not return a birthplace-origin Local Space calculation.'}
              />
            )}
            {activeLocalSpace ? (
              <>
                <div className="flex flex-wrap gap-3 text-xs text-zinc-600 dark:text-zinc-300">
                  <span>Visible rays: {activeLocalSpace.visible_count || 0}</span>
                  <span>Below horizon: {activeLocalSpace.hidden_count || 0}</span>
                  <span>Dominant sectors: {activeLocalSpace.dominant_sectors?.length || 0}</span>
                  <span>Origin: {formatStatusLabel(activeLocalSpace.origin_kind, localSpaceMode)}</span>
                </div>
                <p className="text-sm text-zinc-600 dark:text-zinc-300">{activeLocalSpace.headline || 'No Local Space summary was returned.'}</p>
              </>
            ) : null}
            {Array.isArray(activeLocalSpace?.dominant_sectors) && activeLocalSpace.dominant_sectors.length > 0 ? (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                {activeLocalSpace.dominant_sectors.slice(0, 4).map((sector) => (
                  <div key={sector.sector} className={astroNestedCardCls}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="text-sm font-medium">{sector.sector} Sector</div>
                      <span className="px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide border-zinc-300 bg-zinc-50 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700/30 dark:text-zinc-200">
                        {sector.count} rays
                      </span>
                    </div>
                    <p className="mt-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">{sector.summary}</p>
                    <p className={`mt-2 ${astroMetaTextCls}`}>
                      Lead body: {sector.lead_body || 'n/a'} | Bodies: {(sector.bodies || []).join(', ')}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
          </>
        ) : (
          <WorkspaceEmptyState
            title="Inspect a city to open Local Space."
          />
        )}
      </section>
    );
  } else if (workspaceTab === 'report') {
    workspacePanel = (
      <section className={`p-4 ${railCardCls} space-y-4`}>
        {selectedTarget ? (
          <>
            <WorkspaceHeader
              eyebrow="Workspace"
              title="Report"
              metrics={[
                { label: 'Cards', value: reportCards.length, tone: 'accent' },
                { label: 'Sections', value: reportSections.length },
                selectedTargetLabel ? { label: 'City', value: selectedTargetLabel, tone: 'success' } : null,
              ]}
            />
            {reportPayload?.headline ? (
              <div className={astroBandCls}>
                <div className={astroSectionLabelCls}>Delineation</div>
                <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-300">{reportPayload.headline}</p>
              </div>
            ) : null}
            {reportCards.length ? (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                {reportCards.map((card) => <InsightCard key={card.id} card={card} />)}
              </div>
            ) : null}
            <div className="space-y-3">
              {reportSections.map((section) => <ReportSection key={section.id} section={section} />)}
            </div>
          </>
        ) : (
          <WorkspaceEmptyState
            title="Inspect a city to generate the report."
          />
        )}
      </section>
    );
  }

  const astrocartographySummaryItems = [
    { label: 'Snap', value: snapSummary?.label || snapSummary?.id || '' },
    { label: 'Mode', value: viewMode === 'transit' ? 'Transit' : 'Natal' },
    { label: 'Workspace', value: workspaceTab ? workspaceTab.replace(/-/g, ' ') : '' },
    { label: 'Goal', value: selectedGoal?.label || (!selectedGoalId ? 'General inspection' : '') },
    { label: 'City', value: selectedTargetLabel || '' },
  ];

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-start justify-center p-4 overflow-auto">
      <div className="relative w-full max-w-[92rem]">
        <div className="max-h-[90vh] overflow-auto rounded-[30px] border border-slate-200/80 bg-white/95 p-6 shadow-[0_24px_64px_rgba(15,23,42,0.12)] backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/90">
          <div className="mb-6 rounded-[26px] border border-zinc-200/90 bg-[linear-gradient(135deg,rgba(250,250,250,0.96),rgba(255,255,255,0.98))] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] dark:border-zinc-700 dark:bg-[linear-gradient(135deg,rgba(39,39,42,0.52),rgba(15,23,42,0.42))]">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
              <div className="max-w-3xl">
                <ConsoleBracketEyebrow>astro clock / research workbenches</ConsoleBracketEyebrow>
                <h2 className="mt-3 font-serif text-[2rem] font-medium leading-none tracking-[-0.04em] text-slate-900 dark:text-slate-50">Advanced Workspace</h2>
              </div>
              <div className="ml-auto flex flex-col items-end gap-3 self-start">
                <button onClick={handleClose} className={actionButtonCls}>Close</button>
                <ConsoleModeTabs options={ANALYSIS_MODE_OPTIONS} value={analysisMode} onChange={setAnalysisMode} />
              </div>
            </div>
          </div>

          {analysisMode === 'mundane' ? (
            <MundaneWorkspace open={open} defaultHouseSystem={defaultHouseSystem} />
          ) : analysisMode === 'weather' ? (
            <WeatherWorkspace open={open} defaultHouseSystem={defaultHouseSystem} />
          ) : showSnapPreflight ? (
            <section className={`mx-auto max-w-2xl ${astroSectionCardCls} p-6`}>
              <div className="max-w-xl">
                <ConsoleBracketEyebrow module="astrocartography">setup</ConsoleBracketEyebrow>
                <h3 className="mt-2 text-xl font-semibold text-zinc-900 dark:text-zinc-50">Choose a natal snap before opening the map workspace.</h3>
              </div>

              <div className="mt-5 space-y-4">
                <div className={`${astroMutedPanelCls} space-y-3`}>
                  <div className={`flex items-center justify-between gap-3 ${astroHeaderDividerCls}`}>
                    <div>
                      <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Natal Snap</h4>
                    </div>
                    <button type="button" className={actionButtonCls} onClick={loadSnaps} disabled={loadingSnaps || creatingSnap}>
                      {loadingSnaps ? 'Loading...' : 'Refresh'}
                    </button>
                  </div>

                  <select
                    className={astroInputCls}
                    value={selectedSnapId}
                    onChange={(event) => setSelectedSnapId(event.target.value)}
                    disabled={loadingSnaps || creatingSnap}
                  >
                    <option value="">Select a saved snap...</option>
                    {snapOptions.map((snap) => (
                      <option
                        key={snap.id}
                        value={snap.id}
                        disabled={!isSavedSnapCalculationEligible(snap)}
                      >
                        {snap.label || snap.id}
                        {getSavedSnapIneligibilityLabel(snap)
                          ? ` (${getSavedSnapIneligibilityLabel(snap)})`
                          : ''}
                      </option>
                    ))}
                  </select>
                  {hasSavedSnaps ? (
                    <p className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-400">Saved snaps available.</p>
                  ) : (
                    <p className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                      No saved snaps found yet.
                    </p>
                  )}
                  {snapLoadError ? (
                    <p className="mt-2 text-sm text-red-600">{snapLoadError}</p>
                  ) : null}
                </div>

                <div className={astroMutedPanelCls}>
                  <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Need a first snap?</h4>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {typeof onCreateSnap === 'function' ? (
                      <button
                        type="button"
                        className={primaryActionButtonCls}
                        onClick={handleCreateSnap}
                        disabled={creatingSnap || loadingSnaps}
                      >
                        {creatingSnap ? 'Saving snap...' : 'Save Current Chart as Snap'}
                      </button>
                    ) : null}
                    <button type="button" className={actionButtonCls} onClick={handleClose}>
                      Back to Astro Clock
                    </button>
                  </div>
                </div>

                {createSnapError ? (
                  <p className="text-sm text-red-600">{createSnapError}</p>
                ) : null}
              </div>
            </section>
          ) : (
            <>
          <div className="mb-4">
            <ConsoleCommandBand
              items={astrocartographySummaryItems}
              statusLabel={loadingMap ? 'loading map' : 'active'}
              statusTone={loadingMap ? 'accent' : 'good'}
              trailing={(
                <div className="flex flex-wrap items-center gap-2">
                  <ConsoleModeTabs
                    options={[
                      { id: 'natal', label: 'Natal' },
                      { id: 'transit', label: 'Transit' },
                    ]}
                    value={viewMode}
                    onChange={setViewMode}
                  />
                  <button type="button" className={actionButtonCls} onClick={fetchMap} disabled={!selectedSnapId || loadingMap}>
                    {loadingMap ? 'Loading...' : 'Refresh Map'}
                  </button>
                  {viewMode === 'transit' ? (
                    <button type="button" className={actionButtonCls} onClick={handleApplyTransit}>
                      {transitMode === 'realtime' ? 'Use Current Time' : 'Apply Transit'}
                    </button>
                  ) : null}
                </div>
              )}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-[285px_minmax(0,1.8fr)_330px]">
            <aside className={`p-4 ${railCardCls} space-y-3`}>
              <ConsoleRailSection
                title="Natal Snap"
                eyebrow="reference"
                module="astrocartography"
                headerRight={(
                  <button type="button" className={actionButtonCls} onClick={loadSnaps}>
                    {loadingSnaps ? 'Loading...' : 'Refresh'}
                  </button>
                )}
              >
                <select
                  className={astroInputCls}
                  value={selectedSnapId}
                  onChange={(event) => {
                    setSelectedSnapId(event.target.value);
                    setTargetResult(null);
                    setMapError('');
                  }}
                >
                  <option value="">Select a saved snap...</option>
                  {snapOptions.map((snap) => (
                    <option
                      key={snap.id}
                      value={snap.id}
                      disabled={!isSavedSnapCalculationEligible(snap)}
                    >
                      {snap.label || snap.id}
                      {getSavedSnapIneligibilityLabel(snap)
                        ? ` (${getSavedSnapIneligibilityLabel(snap)})`
                        : ''}
                    </option>
                  ))}
                </select>
                {snapLoadError ? (
                  <p className="mt-2 text-xs text-red-600">{snapLoadError}</p>
                ) : null}
              </ConsoleRailSection>

              {viewMode === 'transit' && (
                <ConsoleRailSection title="Transit Chart Context" eyebrow="transit" module="astrocartography" bodyClassName="mt-3 space-y-3">
                  <div className="flex items-center gap-4 text-sm">
                    <label className="flex items-center gap-2">
                      <input type="radio" name="astrocartography-transit-mode" checked={transitMode === 'realtime'} onChange={() => setTransitMode('realtime')} />
                      <span>Current Time</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="radio" name="astrocartography-transit-mode" checked={transitMode === 'manual'} onChange={() => setTransitMode('manual')} />
                      <span>Manual</span>
                    </label>
                  </div>
                  {transitMode === 'manual' && (
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-xs text-zinc-600 mb-1">Date</label>
                        <input type="date" value={transitDate} onChange={(event) => setTransitDate(event.target.value)} className={astroInputCls} />
                      </div>
                      <div>
                        <label className="block text-xs text-zinc-600 mb-1">Time</label>
                        <input type="time" step="60" value={transitTime} onChange={(event) => setTransitTime(event.target.value)} className={astroInputCls} />
                      </div>
                    </div>
                  )}
                  <div>
                    <label className="block text-xs text-zinc-600 mb-1">Transit chart location</label>
                    <input
                      type="text"
                      placeholder="Location override"
                      value={transitLocation}
                      onChange={(event) => setTransitLocation(event.target.value)}
                      className={astroInputCls}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-600 mb-1">Transit chart time zone</label>
                    <input
                      type="text"
                      placeholder="Time zone override"
                      value={transitTimezone}
                      onChange={(event) => setTransitTimezone(event.target.value)}
                      className={astroInputCls}
                    />
                  </div>
                </ConsoleRailSection>
              )}

              <ConsoleRailSection title="Bodies" eyebrow="filter" module="astrocartography" bodyClassName="mt-3">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {BODY_OPTIONS.map((body) => (
                    <label key={body.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedBodies.includes(body.id)}
                        onChange={() => handleToggleBody(body.id)}
                      />
                      <span>{body.id}</span>
                    </label>
                  ))}
                </div>
                <p className={`mt-3 ${astroMetaTextCls}`}>
                  Sun through Pluto are the core map bodies. North Node uses the mean node; North Node and Chiron are optional experimental interpretive extensions.
                </p>
              </ConsoleRailSection>

              <ConsoleRailSection title="Angles" eyebrow="filter" module="astrocartography" bodyClassName="mt-3">
                <div className="flex flex-wrap gap-3 text-sm">
                  {ANGLE_OPTIONS.map((angle) => (
                    <label key={angle} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedAngles.includes(angle)}
                        onChange={() => handleToggleAngle(angle)}
                      />
                      <span>{angle}</span>
                    </label>
                  ))}
                </div>
              </ConsoleRailSection>

              <ConsoleRailSection
                title="PathFinder Goal"
                eyebrow="goal"
                module="astrocartography"
                headerRight={showGoalsLoading ? <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-500">Loading</span> : null}
              >
                <select
                  className={astroInputCls}
                  value={selectedGoalId}
                  onChange={(event) => setSelectedGoalId(event.target.value)}
                >
                  <option value="">General inspection</option>
                  {groupedGoalOptions.map((group) => (
                    <optgroup key={group.id} label={group.label}>
                      {group.items.map((goal) => (
                        <option key={goal.id} value={goal.id}>
                          {goal.label}{String(goal?.status || '').toLowerCase() === 'experimental' || EXPERIMENTAL_GOAL_META[String(goal?.id || '').toLowerCase()] ? ' (Experimental)' : ''}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                {goalLoadError ? (
                  <p className="text-xs text-red-600">{goalLoadError}</p>
                ) : (
                  !selectedGoalId ? (
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                      General inspection keeps the workspace neutral. Choose a PathFinder goal to rank candidate cities.
                    </p>
                  ) : null
                )}
                {selectedGoal ? (
                  <div className={astroBandCls}>
                    <div className="flex flex-wrap gap-2">
                      {selectedGoalTierLabel ? (
                        <span className="rounded-full border border-zinc-300 bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200">
                          {selectedGoalTierLabel}
                        </span>
                      ) : null}
                      {selectedGoalFamilyLabel ? (
                        <span className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-600 dark:border-zinc-700 dark:bg-zinc-950/40 dark:text-zinc-300">
                          {selectedGoalFamilyLabel}
                        </span>
                      ) : null}
                      {String(selectedGoal?.status || '').toLowerCase() === 'experimental' || selectedGoalExperimentalMeta ? (
                        <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
                          Experimental
                        </span>
                      ) : null}
                    </div>
                    {selectedGoalExperimentalMeta ? (
                      <div className="mt-2 text-amber-800 dark:text-amber-200">
                        <div className={astroSectionLabelCls}>{selectedGoalExperimentalMeta.label}</div>
                        <p className="mt-1 text-[11px] leading-5">{selectedGoalExperimentalMeta.caveat}</p>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </ConsoleRailSection>

              <ConsoleRailSection
                title="Workspace"
                eyebrow="mode"
                module="astrocartography"
                detail="Map tools"
                bodyClassName="mt-3"
              >
                <WorkspaceTabs value={workspaceTab} onChange={setWorkspaceTab} />
              </ConsoleRailSection>

              <ConsoleRailSection
                title="Search Atlas"
                eyebrow="atlas"
                module="astrocartography"
                headerRight={atlasResults?.atlas?.candidate_count != null ? (
                  <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-500">
                    {atlasResults.atlas.candidate_count} candidates
                  </span>
                ) : null}
              >
                <input
                  type="text"
                  placeholder="Optional city or country keyword"
                  value={atlasQuery}
                  onChange={(event) => setAtlasQuery(event.target.value)}
                  className={astroInputCls}
                />
                <input
                  type="text"
                  placeholder="Country code (optional)"
                  value={atlasCountryCode}
                  onChange={(event) => setAtlasCountryCode(event.target.value.toUpperCase().slice(0, 3))}
                  className={`${astroInputCls} uppercase`}
                />
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Region filter</label>
                  <select
                    className={astroInputCls}
                    value={atlasContinentCode}
                    onChange={(event) => setAtlasContinentCode(event.target.value)}
                  >
                    {ATLAS_CONTINENT_OPTIONS.map((option) => (
                      <option key={option.id || 'all'} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-zinc-600 mb-1">Search resolution</label>
                  <select
                    className={astroInputCls}
                    value={atlasResolution}
                    onChange={(event) => setAtlasResolution(event.target.value)}
                  >
                    {ATLAS_RESOLUTION_OPTIONS.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  className={actionButtonCls}
                  onClick={handleSearchAtlas}
                  disabled={loadingAtlas || !selectedGoalId || rankingIneligible || rankingEligibilityPending}
                  title={rankingIneligible ? 'Birth-time uncertainty makes this chart inspection-only.' : undefined}
                >
                  {loadingAtlas
                    ? 'Calculating...'
                    : (rankingIneligible
                      ? 'Inspection Only'
                      : (rankingEligibilityPending ? 'Checking Accuracy' : atlasSearchLabel))}
                </button>
                {rankingIneligible ? (
                  <div className="rounded-[4px] border border-rose-200 bg-rose-50/80 p-3 text-[11px] leading-5 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100">
                    Ranked search is unavailable for this snap because the reported birth-time uncertainty is not ranking-eligible. City inspection remains available.
                  </div>
                ) : null}
                {loadingAtlas && atlasProgress && (
                  <div className={`${astroMutedPanelCls} space-y-2`}>
                    <div className="flex items-center justify-between gap-3 text-[11px]">
                      <span className="font-medium text-zinc-700 dark:text-zinc-200">
                        {atlasProgress.message || 'Running atlas search'}
                      </span>
                      <span className="tabular-nums text-zinc-500 dark:text-zinc-400">
                        {getAtlasProgressPercent(atlasProgress)}%
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
                      <div
                        className="h-full rounded-full bg-zinc-700 transition-[width] duration-300 ease-out dark:bg-zinc-200"
                        style={{ width: `${getAtlasProgressPercent(atlasProgress)}%` }}
                      />
                    </div>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-zinc-500 dark:text-zinc-400">
                      <span>Stage: {String(atlasProgress.stage || 'working').replace(/_/g, ' ')}</span>
                      {Number.isFinite(Number(atlasProgress.done)) && Number.isFinite(Number(atlasProgress.total)) && Number(atlasProgress.total) > 0 ? (
                        <span>{Number(atlasProgress.done)} / {Number(atlasProgress.total)}</span>
                      ) : null}
                      {atlasProgress.candidate_count != null ? (
                        <span>{atlasProgress.candidate_count} candidates</span>
                      ) : null}
                      {atlasProgress.shortlisted_count != null ? (
                        <span>{atlasProgress.shortlisted_count} shortlisted</span>
                      ) : null}
                    </div>
                  </div>
                )}
                {atlasError && <p className="text-xs text-red-600">{atlasError}</p>}
                <p className="text-[11px] text-zinc-600">
                  {selectedAtlasResolution.hint} Region: {selectedAtlasContinent.label}.
                </p>
                <div className="rounded-[4px] border border-amber-200 bg-amber-50/80 p-3 text-[11px] leading-5 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
                  Astrology ranking only. It does not assess personal safety, healthcare, living costs, employment, or visa requirements. Check those separately before travel or relocation.
                </div>
              </ConsoleRailSection>

              <ConsoleRailSection title="Inspect City" eyebrow="target" module="astrocartography">
                <input
                  type="text"
                  placeholder="e.g., London, UK"
                  value={targetQuery}
                  onChange={(event) => setTargetQuery(event.target.value)}
                  className={astroInputCls}
                />
                <button type="button" className={actionButtonCls} onClick={handleInspectTarget} disabled={loadingTarget}>
                  {loadingTarget ? 'Inspecting...' : 'Inspect'}
                </button>
                {targetError && <p className="text-xs text-red-600">{targetError}</p>}
              </ConsoleRailSection>
            </aside>

            {workspacePanel}

            <aside className={`p-4 ${railCardCls} space-y-3`}>
              <ConsoleRailSection title="Inspector" eyebrow="research" module="astrocartography" bodyClassName="mt-3">
                <SelectedCitySummaryCard
                  target={selectedTarget}
                  selectedGoal={selectedGoal}
                  targetResult={targetResult}
                  viewMode={viewMode}
                  onAddToCompare={handleAddToCompare}
                  actionButtonCls={actionButtonCls}
                  rankingEligible={birthTimeAssessment.rankingEligible}
                />
              </ConsoleRailSection>

              <BirthTimeAssessmentPanel
                assessment={birthTimeAssessment}
                sampling={birthTimeSampling}
                lineUncertainty={natalLineUncertainty}
              />

              {showInspectorDetails ? (
                <ReadingPanel
                  title="Natal Baseline"
                  reading={targetResult?.natal?.reading || null}
                  emptyText="No inspected natal lines yet."
                  higherIsWorse={selectedGoalHigherIsWorse}
                />
              ) : null}

              {showInspectorDetails && viewMode === 'transit' && (
                <ReadingPanel
                  title="Transit Activation"
                  reading={targetResult?.transit?.reading || null}
                  emptyText="Apply a transit context to inspect current activation lines."
                  higherIsWorse={selectedGoalHigherIsWorse}
                />
              )}

              {showInspectorDetails ? (
              <ConsoleRailSection title="Parans / Intersections" eyebrow="research" module="astrocartography" bodyClassName="mt-3 space-y-2">
                {(activeParanItems.length || activePrimaryCrossings.length) ? (
                  <div className="space-y-2">
                    {activeParanItems.slice(0, 2).map((item) => (
                      <div key={`${item.canonical_event_id || item.id}-${item.event_kind || 'paran'}`} className={astroNestedCardCls}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-sm font-medium">{item.label}</div>
                          <span className="px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide border-violet-300/80 bg-violet-50 text-violet-700 dark:border-violet-500/40 dark:bg-violet-500/10 dark:text-violet-200">
                            {getEvidenceKindLabel(item, 'Paran')}
                          </span>
                        </div>
                        <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                          {item.distance_km} km away | orb {item.orb_deg} deg
                        </div>
                      </div>
                    ))}
                    {activePrimaryCrossings.slice(0, 2).map((item) => (
                      <div key={`${item.canonical_event_id || item.id}-${item.event_kind || 'crossing'}`} className={astroNestedCardCls}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-sm font-medium">{item.label}</div>
                          <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getZoneBadgeCls(item.zone)}`}>
                            {getEvidenceKindLabel(item, 'Geometry')}
                          </span>
                        </div>
                        <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                          {item.distance_km} km away{
                            Array.isArray(item.point)
                            && Number.isFinite(Number(item.point[0]))
                            && Number.isFinite(Number(item.point[1]))
                              ? ` | ${Number(item.point[0]).toFixed(2)}, ${Number(item.point[1]).toFixed(2)}`
                              : ''
                          }
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={astroBodyTextCls}>No nearby parans or intersections were returned for the current filter set.</p>
                )}
              </ConsoleRailSection>
              ) : null}

              {showInspectorDetails ? (
              <ConsoleRailSection title="Relocation" eyebrow="research" module="astrocartography" bodyClassName="mt-3 space-y-2">
                {relocationHouseSystemCode ? (
                  <div className={astroNestedCardCls}>
                    <div className={astroSectionLabelCls}>Relocation house system</div>
                    <p className="mt-2 text-[12px] leading-5 text-zinc-700 dark:text-zinc-200">
                      {relocationHouseSystemLabel} ({relocationHouseSystemCode})
                    </p>
                    <p className={`mt-1 ${astroMetaTextCls}`}>
                      Relocated house placements depend on this setting; the world map lines do not.
                    </p>
                  </div>
                ) : null}
                {targetResult?.relocation?.available === false || targetResult?.relocation?.relocation_unavailable ? (
                  <div className="rounded-[4px] border border-amber-200 bg-amber-50/80 p-3 text-[11px] leading-5 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
                    <div className={astroSectionLabelCls}>Relocation unavailable</div>
                    <p className="mt-2">
                      {formatServiceError(
                        targetResult?.relocation?.error || targetResult?.relocation?.warnings?.[0],
                        'The service did not return a relocated chart for this target.'
                      )}
                    </p>
                  </div>
                ) : targetResult?.relocation?.summary ? (
                  <div className="space-y-2">
                    {targetResult.relocation.summary.headline && (
                      <div className={astroBandCls}>
                        <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{targetResult.relocation.summary.headline}</p>
                      </div>
                    )}
                    {Array.isArray(targetResult.relocation.summary.angular_planets) && targetResult.relocation.summary.angular_planets.length > 0 && (
                      <div className={astroNestedCardCls}>
                        <div className={`${astroSectionLabelCls} mb-2`}>Angular planets</div>
                        <div className="flex flex-wrap gap-2 text-[11px]">
                          {targetResult.relocation.summary.angular_planets.slice(0, 6).map((item) => (
                            <span key={`${item.planet}-${item.angle}`} className="px-2 py-0.5 rounded-full border border-zinc-300 dark:border-zinc-600">
                              {item.planet} {item.angle}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {Array.isArray(targetResult.relocation.summary.prominent_houses) && targetResult.relocation.summary.prominent_houses.length > 0 && (
                      <div className={astroNestedCardCls}>
                        <div className={`${astroSectionLabelCls} mb-2`}>Prominent houses</div>
                        <div className="space-y-1 text-[11px] text-zinc-600 dark:text-zinc-300">
                          {targetResult.relocation.summary.prominent_houses.slice(0, 3).map((item) => (
                            <div key={`house-${item.house}`}>House {item.house}: {(item.planets || []).join(', ')}</div>
                          ))}
                        </div>
                      </div>
                    )}
                    {Array.isArray(targetResult.relocation.summary.support_notes) && targetResult.relocation.summary.support_notes.length > 0 && (
                      <div className={astroNestedCardCls}>
                        <div className={`${astroSectionLabelCls} mb-2`}>Support metrics</div>
                        <div className="space-y-1 text-[11px] text-zinc-600 dark:text-zinc-300">
                          {targetResult.relocation.summary.support_notes.slice(0, 3).map((note) => (
                            <div key={note}>{note}</div>
                          ))}
                        </div>
                      </div>
                    )}
                    {Array.isArray(targetResult.relocation.summary.caution_notes) && targetResult.relocation.summary.caution_notes.length > 0 && (
                      <div className={astroNestedCardCls}>
                        <div className={`${astroSectionLabelCls} mb-2`}>Cautions</div>
                        <div className="space-y-1 text-[11px] text-zinc-600 dark:text-zinc-300">
                          {targetResult.relocation.summary.caution_notes.slice(0, 2).map((note) => (
                            <div key={note}>{note}</div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className={astroBodyTextCls}>No relocation summary was returned for this target.</p>
                )}
              </ConsoleRailSection>
              ) : null}

              {showInspectorDetails ? (
              <ConsoleRailSection
                title={`${localSpaceMode === 'natal' ? 'Natal' : 'Relocated'} Local Space`}
                eyebrow="research"
                module="astrocartography"
                bodyClassName="mt-3 space-y-2"
              >
                {activeLocalSpace?.rays?.length ? (
                  <div className="space-y-2">
                    <div className={astroBandCls}>
                      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{activeLocalSpace.headline}</p>
                      <p className={`mt-1 ${astroMetaTextCls}`}>
                        Origin: {formatStatusLabel(activeLocalSpace.origin_kind, localSpaceMode)}
                      </p>
                      <p className={`mt-1 ${astroMetaTextCls}`}>
                        Directional Local Space rays are shown separately from world-map lines and do not enter PathFinder scores unless a returned goal model explicitly includes them.
                      </p>
                    </div>
                    {Array.isArray(activeLocalSpace?.dominant_sectors) && activeLocalSpace.dominant_sectors.slice(0, 2).map((sector) => (
                      <div key={`sector-${sector.sector}`} className={astroNestedCardCls}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-sm font-medium">{sector.sector} Sector</div>
                          <span className="px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide border-zinc-300 bg-zinc-50 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700/30 dark:text-zinc-200">
                            {sector.count} rays
                          </span>
                        </div>
                        <div className="mt-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">{sector.summary}</div>
                      </div>
                    ))}
                    {activeLocalSpace.rays.filter((ray) => ray.above_horizon).slice(0, 3).map((ray) => (
                      <div key={ray.id} className={astroNestedCardCls}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-sm font-medium">{ray.label}</div>
                          <span className="px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide border-zinc-300 bg-zinc-50 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700/30 dark:text-zinc-200">
                            {ray.direction_label}
                          </span>
                        </div>
                        <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                          Azimuth {ray.azimuth_deg} deg | Altitude {ray.altitude_deg} deg
                        </div>
                        <div className={`mt-2 ${astroMetaTextCls}`}>{ray.orientation_note}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={astroBodyTextCls}>
                    {localSpaceMode === 'relocated'
                      ? formatServiceError(
                        targetResult?.relocation?.error,
                        'No relocated Local Space rays were returned for this target.'
                      )
                      : 'No birthplace-origin Local Space rays were returned for this chart.'}
                  </p>
                )}
              </ConsoleRailSection>
              ) : null}

              {showAtlasSummary ? (
              <ConsoleRailSection
                title={selectedGoalHigherIsWorse ? 'Lower-pressure candidates' : 'Ranked candidates'}
                eyebrow="atlas"
                module="astrocartography"
                detail={atlasResults?.atlas ? `${atlasResults.atlas.resolution?.label || selectedAtlasResolution.label}${atlasResults.atlas.shortlisted_count != null ? ` / shortlist ${atlasResults.atlas.shortlisted_count}` : ''}${atlasResults.atlas.used_live_augmentation ? ' / live match expansion' : ''}` : ''}
                bodyClassName="mt-3 space-y-2"
              >
                {loadingAtlas ? (
                  <p className={astroBodyTextCls}>Ranking atlas candidates...</p>
                ) : Array.isArray(atlasResults?.results) && atlasResults.results.length > 0 ? (
                  <div className="space-y-2">
                    {atlasResults.results.map((item, index) => {
                      const city = item?.atlas_city || {};
                      const target = buildRankingTarget(item);
                      const targetLabel = getTargetDisplayLabel(target, `Candidate ${index + 1}`);
                      const targetQuery = getAstrocartographyTargetQuery(target);
                      const score = Number(item?.location_score?.score || 0);
                      const reportedAstrologyRank = Number(item?.astrology_rank ?? item?.rank);
                      const astrologyRank = Number.isInteger(reportedAstrologyRank) && reportedAstrologyRank > 0
                        ? reportedAstrologyRank
                        : index + 1;
                      const reportedDisplayOrder = Number(item?.display_rank ?? item?.selection_order);
                      const displayOrder = Number.isInteger(reportedDisplayOrder) && reportedDisplayOrder > 0
                        ? reportedDisplayOrder
                        : index + 1;
                      const ordinal = getAstrocartographyOrdinal(item?.location_score, {
                        rankingEligible: birthTimeAssessment.rankingEligible,
                      });
                      const stability = getAstrocartographyRankStability(item?.location_score || item);
                      const leadFactor = (
                        selectedGoalHigherIsWorse
                          ? item?.location_score?.top_cautions?.[0]?.label
                          : item?.location_score?.top_supports?.[0]?.label
                      ) || item?.natal?.reading?.lead_line?.label || 'No lead factor was reported';
                      return (
                        <div key={buildCompareKey(target) || `${targetQuery || targetLabel}-${index}`} className={astroNestedCardCls}>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-medium">{targetLabel}</div>
                              <div className={`mt-1 flex flex-wrap gap-x-3 gap-y-1 ${astroMetaTextCls}`}>
                                <span>Astrology rank #{astrologyRank}</span>
                                {displayOrder !== astrologyRank ? (
                                  <span>Regional display order #{displayOrder}</span>
                                ) : null}
                              </div>
                              <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                                {city.country_name}{city.population ? ` | Pop ${Number(city.population).toLocaleString()}` : ''}
                              </div>
                              {item?.geographic_group?.label ? (
                                <div className={`mt-1 ${astroMetaTextCls}`}>
                                  Regional group: {item.geographic_group.label}
                                </div>
                              ) : null}
                            </div>
                            <div className="text-right">
                              <span className={`inline-flex px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(score, selectedGoalHigherIsWorse)}`}>
                                {atlasScoreLabel} {ordinal}
                              </span>
                              <div className={`mt-1 ${astroMetaTextCls}`}>Model index {score}</div>
                            </div>
                          </div>
                          <p className="mt-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                            Lead factor: {leadFactor}
                          </p>
                          <p className={astroMetaTextCls} title={stability.detail || undefined}>
                            Rank stability: {stability.label}{stability.detail ? ` · ${stability.detail}` : ''}
                          </p>
                          <div className="mt-2 flex items-center gap-2">
                            <button
                              type="button"
                              className={actionButtonCls}
                              onClick={() => {
                                setTargetQuery(targetQuery || targetLabel);
                                handleInspectTarget(target);
                              }}
                            >
                              Inspect
                            </button>
                            <button
                              type="button"
                              className={actionButtonCls}
                              onClick={() => addTargetToCompare(item)}
                              disabled={rankingIneligible}
                            >
                              Add
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : atlasResults?.atlas?.candidate_count > 0 ? (
                  <p className={astroBodyTextCls}>
                    No ranked candidates were returned for the current goal and region filters. Adjust the filters or inspect a city directly.
                  </p>
                ) : (
                  <p className={astroBodyTextCls}>No atlas candidates were returned.</p>
                )}
              </ConsoleRailSection>
              ) : null}

              {showCompareSummary ? (
              <ConsoleRailSection
                title="Compare Tray"
                eyebrow="compare"
                module="astrocartography"
                headerRight={compareEntries.length > 0 ? (
                  <button type="button" className={actionButtonCls} onClick={() => setCompareTargets([])}>
                    Clear
                  </button>
                ) : null}
                bodyClassName="mt-3 space-y-2"
              >
                {selectedGoal && compareEntries.length > 0 && (
                  <p className={astroMetaTextCls}>
                    {selectedGoalHigherIsWorse ? 'Lower modeled pressure ranks first' : 'Higher model signal ranks first'} for {selectedGoal.label}. Rank stability is reported when available.
                  </p>
                )}
                {loadingCompare ? (
                  <p className={astroBodyTextCls}>Comparing cities...</p>
                ) : compareError ? (
                  <p className="text-sm text-red-600">{compareError}</p>
                ) : selectedGoal && compareResult?.ranking?.length ? (
                  <div className="space-y-2">
                    {compareResult.ranking.map((entry, index) => {
                      const rankingIdentity = resolveCompareRankingIdentity(
                        entry,
                        compareResult,
                        compareEntries,
                      );
                      const rankingTarget = rankingIdentity.target;
                      const entryScore = Number(entry?.location_score?.score ?? entry?.score ?? 0);
                      const entryOrdinal = getAstrocartographyOrdinal(entry?.location_score || entry, {
                        rankingEligible: birthTimeAssessment.rankingEligible,
                      });
                      const entryStability = getAstrocartographyRankStability(entry?.location_score || entry);
                      const entryLeadFactor = (
                        selectedGoalHigherIsWorse
                          ? entry?.top_cautions?.[0]?.label
                          : entry?.top_supports?.[0]?.label
                      ) || entry?.top_supports?.[0]?.label || entry?.top_cautions?.[0]?.label || '';
                      return (
                        <div
                          key={`${buildCompareKey(rankingTarget) || entry.query || entry.label || 'ranking'}-${entry.rank || index + 1}`}
                          className={astroNestedCardCls}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-medium">{entry.rank || index + 1}. {getTargetDisplayLabel(rankingTarget, `Candidate ${index + 1}`)}</div>
                              {entryLeadFactor ? (
                                <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                                  Lead factor: {entryLeadFactor}
                                </div>
                              ) : null}
                              <div className={`mt-1 ${astroMetaTextCls}`} title={entryStability.detail || undefined}>
                                Rank stability: {entryStability.label}{entryStability.detail ? ` · ${entryStability.detail}` : ''}
                              </div>
                            </div>
                            <div className="flex items-start gap-2">
                              <div className="text-right">
                                <span className={`inline-flex px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(entryScore, selectedGoalHigherIsWorse)}`}>
                                  {atlasScoreLabel} {entryOrdinal}
                                </span>
                                <div className={`mt-1 ${astroMetaTextCls}`}>Model index {entryScore}</div>
                              </div>
                              <button
                                type="button"
                                className="rounded-[3px] border border-zinc-300 px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-700/70"
                                disabled={rankingIdentity.ambiguous}
                                title={rankingIdentity.ambiguous
                                  ? 'This response did not return enough identity metadata to remove this same-named target safely.'
                                  : undefined}
                                onClick={() => {
                                  setCompareTargets((prev) => prev.filter((item) => (
                                    !targetsReferToSameLocation(item?.target, rankingTarget)
                                  )));
                                }}
                              >
                                {rankingIdentity.ambiguous ? 'Identity ambiguous' : 'Remove'}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : compareEntries.length ? (
                  <div className="space-y-2">
                    {compareEntries.map((entry, index) => {
                      const natalScore = Number(entry?.natal?.reading?.signal_score || 0);
                      const transitScore = Number(entry?.transit?.reading?.signal_score || 0);
                      const leadNatal = entry?.natal?.reading?.lead_line?.label || 'No natal lead line';
                      const leadTransit = entry?.transit?.reading?.lead_line?.label || '';
                      const targetLabel = getTargetDisplayLabel(entry?.target, `Saved target ${index + 1}`);
                      return (
                        <div key={entry.compareKey} className={astroNestedCardCls}>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-medium">{index + 1}. {targetLabel}</div>
                              <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">{leadNatal}</div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                className="rounded-[3px] border border-zinc-300 px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-700/70"
                                onClick={() => handleRemoveCompare(entry.compareKey)}
                              >
                                Remove
                              </button>
                            </div>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <span
                              className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(natalScore, selectedGoalHigherIsWorse)}`}
                              title={`Natal model index ${natalScore}`}
                            >
                              Natal {getAstrocartographyOrdinal({ score: natalScore })}
                            </span>
                            {entry?.transit?.reading?.signal_score != null ? (
                              <span
                                className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(transitScore, selectedGoalHigherIsWorse)}`}
                                title={`Transit model index ${transitScore}`}
                              >
                                Transit {getAstrocartographyOrdinal({ score: transitScore })}
                              </span>
                            ) : null}
                          </div>
                          {leadTransit && (
                            <p className={`mt-2 ${astroMetaTextCls}`}>Transit lead: {leadTransit}</p>
                          )}
                          <p className={`mt-2 ${astroMetaTextCls}`}>
                            Natal and transit signals remain separate until the server returns a goal-specific ranking.
                          </p>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className={astroBodyTextCls}>
                    Save inspected cities here to compare their reported natal and transit signals.
                  </p>
                )}
              </ConsoleRailSection>
              ) : null}

              <MethodologyPanel
                targetResult={targetResult}
                mapData={mapData}
                atlasResults={atlasResults}
                compareResult={compareResult}
                activeParans={activeParans}
              />

              <ConsoleRailSection title="Rules" eyebrow="guide" module="astrocartography" bodyClassName="mt-3">
                <ul className="space-y-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                  <li>A saved natal snap is required.</li>
                  <li>Birth-time eligibility is taken from returned accuracy metadata; ineligible charts remain inspection-only.</li>
                  <li>Transit and natal signals are displayed separately. The client does not apply a fixed natal/transit blend.</li>
                  <li>Goal-specific ranking order and any transit strategy come from the server response.</li>
                  <li>Distance and paran thresholds come from the returned policy metadata shown above.</li>
                  <li>The compare tray is scoped to the current body, angle, goal, and transit configuration.</li>
                </ul>
              </ConsoleRailSection>
            </aside>
          </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

