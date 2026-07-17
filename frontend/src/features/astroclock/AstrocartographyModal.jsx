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
  { id: 'Sun', short: 'Su' },
  { id: 'Moon', short: 'Mo' },
  { id: 'Mercury', short: 'Me' },
  { id: 'Venus', short: 'Ve' },
  { id: 'Mars', short: 'Ma' },
  { id: 'Jupiter', short: 'Ju' },
  { id: 'Saturn', short: 'Sa' },
  { id: 'Uranus', short: 'Ur' },
  { id: 'Neptune', short: 'Ne' },
  { id: 'Pluto', short: 'Pl' },
  { id: 'North Node', short: 'NN' },
  { id: 'Chiron', short: 'Ch' },
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
    hint: 'Fastest scan. Capitals, admin seats, and the largest metros.',
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
const HIDDEN_FRONTEND_GOAL_IDS = new Set([
  'travel_fun',
  'travel_relax',
]);
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
  return goals.filter((goal) => !HIDDEN_FRONTEND_GOAL_IDS.has(String(goal?.id || '').trim().toLowerCase()));
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
  const label = getAstrocartographyTargetLabel(target) || 'Selected location';
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

function getAtlasProgressPercent(progress) {
  const value = Number(progress?.percent);
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value * 100)));
}

function buildCompareKey(target) {
  if (!target) return '';
  return [
    getAstrocartographyTargetLabel(target),
    target.latitude,
    target.longitude,
  ].map((value) => String(value ?? '')).join('|');
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

function getSignalBadgeCls(score) {
  if (score >= 70) {
    return 'border-emerald-300/80 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-200';
  }
  if (score >= 40) {
    return 'border-amber-300/80 bg-amber-50 text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200';
  }
  return 'border-zinc-300/80 bg-zinc-50 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700/30 dark:text-zinc-200';
}

function getCompareSignal(entry) {
  const natalScore = Number(entry?.natal?.reading?.signal_score || 0);
  const transitScore = Number(entry?.transit?.reading?.signal_score || 0);
  return Math.round(natalScore + (transitScore * 0.35));
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
}) {
  if (!target) {
    return (
      <div className={`${astroMutedPanelCls} text-sm text-zinc-600 dark:text-zinc-300`}>
        No city selected.
      </div>
    );
  }

  const targetLabel = getAstrocartographyTargetLabel(target) || 'Selected location';
  const activeMode = viewMode === 'transit' && targetResult?.transit ? 'Transit overlay' : 'Natal baseline';
  const locationScore = Number(targetResult?.location_score?.score || 0);
  const natalSignal = Number(targetResult?.natal?.reading?.signal_score || 0);
  const transitSignal = Number(targetResult?.transit?.reading?.signal_score || 0);
  const leadSupport =
    targetResult?.location_score?.top_supports?.[0]?.label
    || targetResult?.natal?.reading?.lead_line?.label
    || '';
  const scoreLabel = selectedGoal?.score_polarity === 'higher_is_worse' ? 'Risk score' : 'Goal score';

  return (
    <div className={`${astroSectionCardCls} space-y-3`}>
      <div className={`flex items-start justify-between gap-3 ${astroHeaderDividerCls}`}>
        <div className="min-w-0">
          <ConsoleBracketEyebrow module="astrocartography">selected city</ConsoleBracketEyebrow>
          <div className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">{targetLabel}</div>
          <div className="mt-1 text-[12px] text-zinc-600 dark:text-zinc-300">
            {target.latitude.toFixed(4)}, {target.longitude.toFixed(4)}
          </div>
        </div>
        <button type="button" className={actionButtonCls} onClick={onAddToCompare}>
          Add To Compare
        </button>
      </div>
      {leadSupport ? (
        <div className={astroBandCls}>
          <div className={astroSectionLabelCls}>Lead support</div>
          <p className="mt-2 text-sm leading-6 text-zinc-700 dark:text-zinc-200">{leadSupport}</p>
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-2 xl:grid-cols-3">
        <MetricChip label="Mode" value={activeMode} tone="default" />
        {selectedGoal?.label ? <MetricChip label="Goal" value={selectedGoal.label} tone="accent" /> : null}
        <MetricChip label="Natal" value={natalSignal} tone="success" />
        {viewMode === 'transit' && targetResult?.transit?.reading?.signal_score != null ? (
          <MetricChip label="Transit" value={transitSignal} tone="accent" />
        ) : null}
        {targetResult?.location_score?.score != null ? <MetricChip label={scoreLabel} value={locationScore} tone="warning" /> : null}
      </div>
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
      <p className="mt-2 text-[12px] leading-6 text-zinc-700 dark:text-zinc-200">{row.summary}</p>
      <p className={`mt-2 ${astroMetaTextCls}`}>{row.caution}</p>
    </div>
  );
}

function ReadingPanel({ title, reading, emptyText }) {
  return (
    <ConsoleRailSection
      title={title}
      eyebrow="reading"
      module="astrocartography"
      headerRight={reading?.signal_score != null ? (
        <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(Number(reading.signal_score) || 0)}`}>
          Signal {reading.signal_score}
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
  const atlasSessionIdRef = useRef('');

const actionButtonCls = 'rounded-[3px] border border-zinc-300 bg-white px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-700 shadow-none hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900/45 dark:text-zinc-100 dark:hover:bg-zinc-900/70';
const primaryActionButtonCls = 'rounded-[3px] border border-zinc-900 bg-zinc-900 px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200';
const railCardCls = 'rounded-[4px] border border-zinc-200/90 bg-white/96 dark:border-zinc-700/90 dark:bg-zinc-900/88 backdrop-blur-xl shadow-none';
  const beginAtlasRun = useCallback(() => {
    atlasRunIdRef.current += 1;
    return atlasRunIdRef.current;
  }, []);
  const isAtlasRunActive = useCallback((runId) => (
    mountedRef.current && atlasRunIdRef.current === runId
  ), []);
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
    atlasRunIdRef.current += 1;
    setLoadingAtlas(false);
    setTrackedAtlasSessionId('');
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
    onClose?.();
  }, [cancelAtlasSearchSession, onClose, setTrackedAtlasSessionId]);

  useEffect(() => () => {
    const activeSessionId = atlasSessionIdRef.current;
    mountedRef.current = false;
    atlasRunIdRef.current += 1;
    atlasSessionIdRef.current = '';
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [cancelAtlasSearchSession]);

  useEffect(() => {
    if (open) return;
    const activeSessionId = atlasSessionIdRef.current;
    atlasRunIdRef.current += 1;
    setLoadingAtlas(false);
    setTrackedAtlasSessionId('');
    setCreatingSnap(false);
    setCreateSnapError('');
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [cancelAtlasSearchSession, open, setTrackedAtlasSessionId]);

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
    atlasRunIdRef.current += 1;
    setLoadingAtlas(false);
    const seed = initialTransitContext || {};
    setSelectedSnapId(String(activeSnapId || seed.snapId || ''));
    setViewMode('natal');
    setTransitMode('realtime');
    setSelectedGoalId('');
    setWorkspaceTab('map');
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
  }, [open, initialTransitContext, activeSnapId, setTrackedAtlasSessionId]);

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
    setLoadingMap(true);
    setMapError('');
    try {
      const res = await AstroClockAPI.getAstrocartographyMap({
        natalSnapId: selectedSnapId,
        houseSystem,
        bodies: selectedBodies,
        angles: selectedAngles,
        ...(activeTransitRequest || {}),
      });
      if (!res?.success) {
        throw new Error('Failed to load astrocartography map.');
      }
      setMapData(res.data || null);
    } catch (error) {
      setMapData(null);
      setMapError(describeAstrocartographyError(error, 'Failed to load astrocartography map.'));
    } finally {
      setLoadingMap(false);
    }
  }, [activeTransitRequest, houseSystem, selectedAngles, selectedBodies, selectedSnapId]);

  useEffect(() => {
    if (!open || analysisMode !== 'astrocartography' || !selectedSnapId) return;
    fetchMap();
  }, [analysisMode, fetchMap, open, selectedSnapId]);

  useEffect(() => {
    if (!open) return;
    const activeSessionId = atlasSessionIdRef.current;
    atlasRunIdRef.current += 1;
    setLoadingAtlas(false);
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
  }, [cancelAtlasSearchSession, filterSignature, open, selectedSnapId, setTrackedAtlasSessionId]);

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
    const nextQuery = resolveAstrocartographyTargetQuery(queryOverride, targetQuery);
    if (!selectedSnapId) {
      setTargetError('Choose a saved natal snap first.');
      return;
    }
    if (!nextQuery) {
      setTargetError('Enter a city or location to inspect.');
      return;
    }
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
        ...(activeTransitRequest || {}),
      });
      if (!res?.success) {
        throw new Error('Failed to inspect location.');
      }
      setTargetResult(res.data || null);
      setTargetQuery(nextQuery);
    } catch (error) {
      setTargetResult(null);
      setTargetError(error?.message || 'Failed to inspect location.');
    } finally {
      setLoadingTarget(false);
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
    const normalizedTarget = {
      ...payload.target,
      label: getAstrocartographyTargetLabel(payload.target),
      query: getAstrocartographyTargetQuery(payload.target),
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
    const runId = beginAtlasRun();
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
            const progressRes = await AstroClockAPI.getAstrocartographyAtlasSearchProgress(sessionId);
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

      const resultRes = await AstroClockAPI.getAstrocartographyAtlasSearchResult(sessionId);
      if (!isAtlasRunActive(runId)) return;
      if (resultRes?.data?.failed) {
        throw new Error(resultRes.data.error || 'Atlas search failed.');
      }
      if (!resultRes?.data?.ready || !resultRes?.data?.result) {
        throw new Error('Atlas search did not return a final result.');
      }
      setAtlasResults(resultRes.data.result || null);
    } catch (error) {
      if (!isAtlasRunActive(runId)) return;
      setAtlasResults(null);
      setAtlasError(describeAstrocartographyError(error, 'Failed to search atlas candidates.'));
    } finally {
      if (isAtlasRunActive(runId)) {
        setLoadingAtlas(false);
      }
    }
  }, [activeTransitRequest, atlasContinentCode, atlasCountryCode, atlasQuery, atlasResolution, beginAtlasRun, cancelAtlasSearchSession, houseSystem, isAtlasRunActive, selectedAngles, selectedBodies, selectedGoalId, selectedSnapId, setTrackedAtlasSessionId]);

  const natalLines = mapData?.map?.natal_lines || [];
  const transitLines = mapData?.map?.transit_lines || [];
  const globalParanTracks = Array.isArray(mapData?.map?.global_parans?.tracks) ? mapData.map.global_parans.tracks : [];
  const transitGlobalParanTracks = Array.isArray(mapData?.map?.transit_global_parans?.tracks) ? mapData.map.transit_global_parans.tracks : [];
  const selectedTarget = targetResult?.target || null;
  const hasSavedSnaps = Array.isArray(snapOptions) && snapOptions.length > 0;

  useEffect(() => {
    if (!open || selectedSnapId || !hasSavedSnaps) return;
    const defaultSnapId = String(activeSnapId || snapOptions[0]?.id || '');
    if (defaultSnapId) {
      setSelectedSnapId(defaultSnapId);
    }
  }, [activeSnapId, hasSavedSnaps, open, selectedSnapId, snapOptions]);

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
  const atlasPinsLabel = selectedGoalHigherIsWorse ? 'Lowest-risk pins' : 'Best-match pins';
  const atlasSearchLabel = selectedGoalHigherIsWorse ? 'Search Lowest Risk' : 'Search Best Cities';
  const atlasScoreLabel = selectedGoalHigherIsWorse ? 'Risk score' : 'Goal score';

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
  const activeLocalSpace = activeTargetMode === 'transit'
    ? targetResult?.transit?.local_space || targetResult?.natal?.local_space || null
    : targetResult?.natal?.local_space || null;
  const reportPayload = targetResult?.report || null;

  const compareEntries = useMemo(() => {
    return [...compareTargets].sort((left, right) => {
      const rightScore = getCompareSignal(right);
      const leftScore = getCompareSignal(left);
      if (rightScore !== leftScore) return rightScore - leftScore;
      return getAstrocartographyTargetLabel(left?.target).localeCompare(getAstrocartographyTargetLabel(right?.target));
    });
  }, [compareTargets]);
  const selectedTargetLabel = getAstrocartographyTargetLabel(selectedTarget) || '';
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
      setCompareResult(null);
      setCompareError('');
      return;
    }
    setLoadingCompare(true);
    setCompareError('');
    try {
      const targetLocations = compareTargets
        .map((entry) => getAstrocartographyTargetQuery(entry?.target) || getAstrocartographyTargetLabel(entry?.target))
        .filter((value) => typeof value === 'string' && value.trim());
      const res = await AstroClockAPI.compareAstrocartographyTargets({
        natalSnapId: selectedSnapId,
        houseSystem,
        goalId: selectedGoalId,
        bodies: selectedBodies,
        angles: selectedAngles,
        targetLocations,
        ...(activeTransitRequest || {}),
      });
      if (!res?.success) {
        throw new Error('Failed to compare locations.');
      }
      setCompareResult(res.data || null);
    } catch (error) {
      setCompareResult(null);
      setCompareError(error?.message || 'Failed to compare locations.');
    } finally {
      setLoadingCompare(false);
    }
  }, [activeTransitRequest, compareTargets, houseSystem, selectedAngles, selectedBodies, selectedGoalId, selectedSnapId]);

  useEffect(() => {
    if (!open || analysisMode !== 'astrocartography') return;
    if (!selectedGoalId || compareTargets.length < 2) {
      setCompareResult(null);
      setCompareError('');
      return;
    }
    fetchCompare();
  }, [analysisMode, compareTargets, fetchCompare, open, selectedGoalId]);

  useEffect(() => {
    if (!open) return;
    setTargetResult(null);
    setTargetError('');
    setCompareTargets([]);
    setCompareResult(null);
    setCompareError('');
  }, [open, selectedGoalId]);

  useEffect(() => {
    if (!open) return;
    const activeSessionId = atlasSessionIdRef.current;
    atlasRunIdRef.current += 1;
    setLoadingAtlas(false);
    setAtlasResults(null);
    setAtlasError('');
    setTrackedAtlasSessionId('');
    setAtlasProgress(null);
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [atlasResolution, cancelAtlasSearchSession, open, selectedGoalId, setTrackedAtlasSessionId]);

  useEffect(() => {
    if (!open || analysisMode === 'astrocartography') return;
    const activeSessionId = atlasSessionIdRef.current;
    atlasRunIdRef.current += 1;
    setLoadingAtlas(false);
    setAtlasResults(null);
    setAtlasError('');
    setTrackedAtlasSessionId('');
    setAtlasProgress(null);
    if (activeSessionId) {
      void cancelAtlasSearchSession(activeSessionId);
    }
  }, [analysisMode, cancelAtlasSearchSession, open, setTrackedAtlasSessionId]);

  const activeIntersectionPoints = Array.isArray(activeIntersections?.geometry_points) ? activeIntersections.geometry_points : [];
  const activeParanPoints = Array.isArray(activeParans?.items) ? activeParans.items.filter((item) => item?.point) : [];
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
            const targetLabel = getAstrocartographyTargetLabel(target) || `Match ${index + 1}`;
            if (typeof target.latitude !== 'number' || typeof target.longitude !== 'number') return null;
            return (
              <CircleMarker
                key={`atlas-pin-${targetLabel || index}`}
                center={[target.latitude, target.longitude]}
                radius={Math.max(4, 8 - index)}
                pathOptions={{ color: '#0f766e', weight: 2, fillColor: '#10b981', fillOpacity: 0.55 }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-medium">{targetLabel}</div>
                    <div>Rank {index + 1} | {atlasScoreLabel} {item?.location_score?.score ?? 'n/a'}</div>
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
                      key={item.id}
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
                      key={`${item.id}-paran`}
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
              title="Local Space"
              metrics={[
                { label: 'Visible', value: activeLocalSpace?.visible_count || 0, tone: 'success' },
                { label: 'Hidden', value: activeLocalSpace?.hidden_count || 0 },
                { label: 'Sectors', value: activeLocalSpace?.dominant_sectors?.length || 0, tone: 'accent' },
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
                {(activeLocalSpace?.range_rings_km || []).map((radiusKm) => (
                  <Circle
                    key={`local-space-ring-${radiusKm}`}
                    center={[selectedTarget.latitude, selectedTarget.longitude]}
                    radius={Number(radiusKm) * 1000}
                    pathOptions={{ color: '#94a3b8', weight: 1, opacity: 0.3, dashArray: '4 10' }}
                  />
                ))}
                {activeLocalSpaceRays.map((ray) => (
                  (ray.segments || []).map((segment, idx) => (
                    <Polyline
                      key={`local-space-${ray.id}-${idx}`}
                      positions={segment}
                      pathOptions={{ color: ray.color || '#64748b', weight: 2.2, opacity: ray.above_horizon ? 0.92 : 0.35, dashArray: ray.above_horizon ? undefined : '6 8' }}
                    />
                  ))
                ))}
                <TargetPin target={selectedTarget} />
              </MapContainer>
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-zinc-600 dark:text-zinc-300">
              <span>Visible rays: {activeLocalSpace?.visible_count || 0}</span>
              <span>Below horizon: {activeLocalSpace?.hidden_count || 0}</span>
              <span>Dominant sectors: {activeLocalSpace?.dominant_sectors?.length || 0}</span>
              <span>Mode: {activeTargetMode}</span>
            </div>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">{activeLocalSpace?.headline || 'No Local Space ray set yet.'}</p>
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
                      <option key={snap.id} value={snap.id}>
                        {snap.label || snap.id}
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
                    <option key={snap.id} value={snap.id}>
                      {snap.label || snap.id}
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
                      <span className="inline-flex items-center gap-2"><span className="min-w-[1.75rem] rounded-md border border-zinc-300 bg-zinc-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-600 dark:border-zinc-600 dark:bg-zinc-900/60 dark:text-zinc-300">{body.short}</span><span>{body.id}</span></span>
                    </label>
                  ))}
                </div>
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
                          {goal.label}
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
                      General inspection keeps the workspace neutral. Choose a PathFinder goal to enable Search Best Cities.
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
                    </div>
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
                <button type="button" className={actionButtonCls} onClick={handleSearchAtlas} disabled={loadingAtlas || !selectedGoalId}>
                  {loadingAtlas ? 'Calculating...' : atlasSearchLabel}
                </button>
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
                />
              </ConsoleRailSection>

              {showInspectorDetails ? (
                <ReadingPanel
                  title="Natal Baseline"
                  reading={targetResult?.natal?.reading || null}
                  emptyText="No inspected natal lines yet."
                />
              ) : null}

              {showInspectorDetails && viewMode === 'transit' && (
                <ReadingPanel
                  title="Transit Activation"
                  reading={targetResult?.transit?.reading || null}
                  emptyText="Apply a transit context to inspect current activation lines."
                />
              )}

              {showInspectorDetails ? (
              <ConsoleRailSection title="Parans / Intersections" eyebrow="research" module="astrocartography" bodyClassName="mt-3 space-y-2">
                {(activeParans?.items?.length || activeIntersections?.primary_crossings?.length) ? (
                  <div className="space-y-2">
                    {Array.isArray(activeParans?.items) && activeParans.items.slice(0, 2).map((item) => (
                      <div key={item.id} className={astroNestedCardCls}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-sm font-medium">{item.label}</div>
                          <span className="px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide border-violet-300/80 bg-violet-50 text-violet-700 dark:border-violet-500/40 dark:bg-violet-500/10 dark:text-violet-200">
                            paran
                          </span>
                        </div>
                        <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                          {item.distance_km} km away | orb {item.orb_deg} deg
                        </div>
                      </div>
                    ))}
                    {activeIntersections?.primary_crossings?.slice(0, 2).map((item) => (
                      <div key={item.id} className={astroNestedCardCls}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-sm font-medium">{item.label}</div>
                          <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getZoneBadgeCls(item.zone)}`}>
                            geometry
                          </span>
                        </div>
                        <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                          {item.distance_km} km away{item.point ? ` | ${item.point[0].toFixed(2)}, ${item.point[1].toFixed(2)}` : ''}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={astroBodyTextCls}>No strong nearby parans or intersections surfaced for the current filter set.</p>
                )}
              </ConsoleRailSection>
              ) : null}

              {showInspectorDetails ? (
              <ConsoleRailSection title="Relocation" eyebrow="research" module="astrocartography" bodyClassName="mt-3 space-y-2">
                {targetResult?.relocation?.summary ? (
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
                  <p className={astroBodyTextCls}>No goal selected.</p>
                )}
              </ConsoleRailSection>
              ) : null}

              {showInspectorDetails ? (
              <ConsoleRailSection title="Local Space" eyebrow="research" module="astrocartography" bodyClassName="mt-3 space-y-2">
                {activeLocalSpace?.rays?.length ? (
                  <div className="space-y-2">
                    <div className={astroBandCls}>
                      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{activeLocalSpace.headline}</p>
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
                  <p className={astroBodyTextCls}>Inspect a city to derive Local Space rays.</p>
                )}
              </ConsoleRailSection>
              ) : null}

              {showAtlasSummary ? (
              <ConsoleRailSection
                title="Best Matches"
                eyebrow="atlas"
                module="astrocartography"
                detail={atlasResults?.atlas ? `${atlasResults.atlas.resolution?.label || selectedAtlasResolution.label}${atlasResults.atlas.shortlisted_count != null ? ` / shortlist ${atlasResults.atlas.shortlisted_count}` : ''}${atlasResults.atlas.used_live_augmentation ? ' / live match expansion' : ''}` : ''}
                bodyClassName="mt-3 space-y-2"
              >
                {loadingAtlas ? (
                  <p className={astroBodyTextCls}>Searching atlas...</p>
                ) : Array.isArray(atlasResults?.results) && atlasResults.results.length > 0 ? (
                  <div className="space-y-2">
                    {atlasResults.results.map((item, index) => {
                      const city = item?.atlas_city || {};
                      const target = item?.target || {};
                      const targetLabel = getAstrocartographyTargetLabel(target) || `Match ${index + 1}`;
                      const targetQuery = getAstrocartographyTargetQuery(target);
                      const score = Number(item?.location_score?.score || 0);
                      const leadSupport = item?.location_score?.top_supports?.[0]?.label || item?.natal?.reading?.lead_line?.label || 'No clear lead support';
                      return (
                        <div key={`${targetQuery || targetLabel}-${index}`} className={astroNestedCardCls}>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-medium">{index + 1}. {targetLabel}</div>
                              <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                                {city.country_name}{city.population ? ` | Pop ${Number(city.population).toLocaleString()}` : ''}
                              </div>
                            </div>
                            <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(score)}`}>
                              Score {score}
                            </span>
                          </div>
                          <p className="mt-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                            Lead support: {leadSupport}
                          </p>
                          <div className="mt-2 flex items-center gap-2">
                            <button
                              type="button"
                              className={actionButtonCls}
                              onClick={() => {
                                const nextTargetQuery = targetQuery || targetLabel;
                                setTargetQuery(nextTargetQuery);
                                handleInspectTarget(nextTargetQuery);
                              }}
                            >
                              Inspect
                            </button>
                            <button
                              type="button"
                              className={actionButtonCls}
                              onClick={() => addTargetToCompare(item)}
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
                    No cities crossed the current signal floor for {selectedGoal?.label || 'this goal'}. Expand the region, raise the resolution, or inspect a city directly.
                  </p>
                ) : (
                  <p className={astroBodyTextCls}>No atlas results.</p>
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
                    Ranking active for {selectedGoal.label}.
                  </p>
                )}
                {loadingCompare ? (
                  <p className={astroBodyTextCls}>Comparing cities...</p>
                ) : compareError ? (
                  <p className="text-sm text-red-600">{compareError}</p>
                ) : selectedGoal && compareResult?.ranking?.length ? (
                  <div className="space-y-2">
                    {compareResult.ranking.map((entry) => (
                      <div key={entry.query || entry.label} className={astroNestedCardCls}>
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-sm font-medium">{entry.rank}. {entry.label}</div>
                            {entry.top_supports?.[0]?.label && (
                              <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                                Lead support: {entry.top_supports[0].label}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(Number(entry.score) || 0)}`}>
                              Score {entry.score}
                            </span>
                            <button
                              type="button"
                              className="rounded-[3px] border border-zinc-300 px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-700/70"
                              onClick={() => {
                                setCompareTargets((prev) => prev.filter((item) => {
                                  const query = getAstrocartographyTargetQuery(item?.target) || getAstrocartographyTargetLabel(item?.target);
                                  return query !== (entry.query || entry.label);
                                }));
                              }}
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                        {entry.top_cautions?.[0]?.label && (
                          <p className={`mt-2 ${astroMetaTextCls}`}>
                            Main caution: {entry.top_cautions[0].label}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : compareEntries.length ? (
                  <div className="space-y-2">
                    {compareEntries.map((entry, index) => {
                      const compareScore = getCompareSignal(entry);
                      const leadNatal = entry?.natal?.reading?.lead_line?.label || 'No natal lead line';
                      const leadTransit = entry?.transit?.reading?.lead_line?.label || '';
                      const targetLabel = getAstrocartographyTargetLabel(entry?.target) || `Saved target ${index + 1}`;
                      return (
                        <div key={entry.compareKey} className={astroNestedCardCls}>
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-medium">{index + 1}. {targetLabel}</div>
                              <div className="mt-1 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">{leadNatal}</div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-wide ${getSignalBadgeCls(compareScore)}`}>
                                Index {compareScore}
                              </span>
                              <button
                                type="button"
                                className="rounded-[3px] border border-zinc-300 px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-700/70"
                                onClick={() => handleRemoveCompare(entry.compareKey)}
                              >
                                Remove
                              </button>
                            </div>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-zinc-600 dark:text-zinc-300">
                            <span>Natal {entry?.natal?.reading?.signal_score || 0}</span>
                            {entry?.transit?.reading?.signal_score != null && <span>Transit {entry.transit.reading.signal_score}</span>}
                          </div>
                          {leadTransit && (
                            <p className={`mt-2 ${astroMetaTextCls}`}>Transit lead: {leadTransit}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className={astroBodyTextCls}>
                    Save inspected cities here to compare their current natal and transit signal balance.
                  </p>
                )}
              </ConsoleRailSection>
              ) : null}

              <ConsoleRailSection title="Rules" eyebrow="guide" module="astrocartography" bodyClassName="mt-3">
                <ul className="space-y-2 text-[12px] leading-6 text-zinc-600 dark:text-zinc-300">
                  <li>A saved natal snap is required.</li>
                  <li>Transit mode overlays the natal base and does not replace it.</li>
                  <li>Primary reading radius: 300 km.</li>
                  <li>Extended reading radius: 500 km.</li>
                  <li>Compare tray is scoped to the current line and transit configuration.</li>
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

