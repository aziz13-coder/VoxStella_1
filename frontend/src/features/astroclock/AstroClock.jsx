import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, Polygon, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Ensure default marker icons load under Vite/Electron bundling
try {
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
  });
} catch(_) {}
import SketchWheel from '../../components/wheel/SketchWheel';
import { AstroClockAPI } from './api.mjs';
import ReceptionsTile from './ReceptionsTile.jsx';
import MetricsTile from './MetricsTile.jsx';
import DegreeHitsTile from './DegreeHitsTile.jsx';
import AlmutenTile from './AlmutenTile.jsx';
import TraitProfileModal from './TraitProfileModal.jsx';
import SynastryModal from './SynastryModal.jsx';
import TransitsModal from './TransitsModal.jsx';
import ElectionModal from './ElectionModal.jsx';
import AstrocartographyModal from './AstrocartographyModal.jsx';
import ResearchMode from './ResearchMode.jsx';
import { transformDashboard, degString, aspectSymbol } from './transform.mjs';
import AspectAnalysisModal from './AspectAnalysisModal.jsx';
import CompassTile from './CompassTile.jsx';
import AsteroidsTile from './AsteroidsTile.jsx';
import NamePromptModal from './NamePromptModal.jsx';
import { cleanForensicDisplayText, deriveForensicReplayAxes, formatForensicDisplayLabel } from './forensicReplayAxes.mjs';
import { formatForensicAspectLabels } from './forensicAspectSummary.mjs';
import { buildAbductionCueReportLines, buildAbductionCueSummary } from './forensicAbductionCues.mjs';
import {
  buildProcessedAbductionBearings,
  formatAbductionBearingRoleLabel,
  getAbductionLegendEntries,
  getAbductionRoleStyle,
  normalizeCoordinateInput,
} from './forensicAbductionMap.mjs';
import {
  buildRelationshipDisplayRows,
  summarizeForensicRelationshipLink,
} from './forensicRelationshipLink.mjs';
import { summarizeForensicSurvivalSignal } from './forensicSurvivalSignal.mjs';
import {
  formatAstroClockTimezoneLabel,
  readAstroClockWarmState,
  resolveAstroClockTimezone,
  resolveManualSnapshotTarget,
  shouldApplyAstroClockRequest,
  writeAstroClockWarmState,
} from './astroClockViewState.mjs';
import { redirectToPremiumUpgrade, shouldGatePremiumFeature } from '../../utils/premiumAccess.mjs';

// Robust clipboard helper for Electron/packaged builds
async function safeCopyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      ta.style.pointerEvents = 'none';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch (_) {
      return false;
    }
  }
}

function getActionErrorMessage(error, fallbackMessage) {
  const rawMessage = typeof error?.message === 'string' ? error.message.trim() : '';
  return rawMessage || fallbackMessage;
}

function getClockLoadErrorMessage(error, fallbackMessage) {
  const rawMessage = typeof error?.message === 'string' ? error.message.trim() : '';
  if (/^Request timed out after \d+s$/i.test(rawMessage)) {
    return 'Astro Clock refresh took too long. Try Refresh again.';
  }
  return rawMessage || fallbackMessage;
}

const TIME_LOCALE = 'en-GB';

const PlanetSymbols = {
  Sun: '☉',
  Moon: '☾',
  Mercury: '☿',
  Venus: '♀',
  Mars: '♂',
  Jupiter: '♃',
  Saturn: '♄',
  Uranus: '♅',
  Neptune: '♆',
  Pluto: '♇',
  'North Node': '☊',
};

function formatHM(iso) {
  if (!iso) return '';
  try {
    const dt = new Date(iso);
    return new Intl.DateTimeFormat(TIME_LOCALE, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      hourCycle: 'h23'
    }).format(dt);
  } catch { return ''; }
}

function hourProgress(startIso, endIso) {
  try {
    const now = Date.now();
    const s = Date.parse(startIso);
    const e = Date.parse(endIso);
    if (!isFinite(s) || !isFinite(e) || e <= s) return 0;
    return Math.max(0, Math.min(100, ((now - s) / (e - s)) * 100));
  } catch { return 0; }
}

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';

const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
function signFromLon(lon=0){ const n=((Math.floor(lon/30))%12+12)%12; return signs[n]; }
function degreeTextFromLon(lon=0){ const d=Math.floor(lon%30); const m=Math.floor(((lon%1)*60)); return `${d}°${String(m).padStart(2,'0')}'`; }
function formatSurvivabilityBandLabel(value){
  const raw = String(value || '').trim();
  if (!raw) return '';
  const labels = {
    release_favored: 'release-favored',
    risk_loaded_survival: 'risk-loaded survival',
    fatal_pressure_dominant: 'fatal-pressure dominant',
    nonfatal_tilt: 'non-fatal tilt',
    mixed_nonfatal: 'mixed / non-fatal',
  };
  return labels[raw] || raw.replace(/_/g, ' ');
}

function DispositorsCard({ data, includeModern }){
  // Use backend-provided dispositor chains to avoid duplicating reception logic
  const DISP = (data && data.dispositors) || {};
  const baseAnchors = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn'];
  const modernAnchors = includeModern ? ['Uranus','Neptune','Pluto'] : [];
  const anchors = [...baseAnchors, ...modernAnchors].filter(p => DISP[p]);

  const chip = (name) => (
    <span className="px-1.5 py-0.5 rounded-full border border-zinc-200">{PlanetSymbols[name] || name}</span>
  );

  // Traditional rulers for domicile check (kept in sync with backend)
  const signRuler = {
    'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury', 'Cancer': 'Moon', 'Leo': 'Sun', 'Virgo': 'Mercury',
    'Libra': 'Venus', 'Scorpio': 'Mars', 'Sagittarius': 'Jupiter', 'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter'
  };
  const planetSign = (planetName) => {
    try {
      const pl = (data?.planets || []).find(p => p.planet === planetName);
      return pl?.sign || null;
    } catch (_) { return null; }
  };
  const isDomicile = (planetName) => {
    const sign = planetSign(planetName);
    if (!sign) return false;
    return signRuler[sign] === planetName;
  };

  return (
    <div className="space-y-3 text-sm">
      {anchors.map((anchor) => {
        const info = DISP[anchor] || {};
        const chain = Array.isArray(info.chain) && info.chain.length ? info.chain : [anchor];
        const finalDisp = info.final_dispositor || chain[chain.length - 1] || anchor;
        const domAnchor = isDomicile(anchor);
        const domFinal = isDomicile(finalDisp);
        const tooltip = (() => {
          try {
            const parts = chain.map((nm) => {
              const s = planetSign(nm);
              return `${nm}${s ? ` (${s})` : ''}`;
            });
            const tail = domAnchor ? ' — domicile' : (domFinal ? ' — final in domicile' : '');
            return parts.join(' → ') + tail;
          } catch(_) { return chain.join(' → '); }
        })();
        return (
          <div key={anchor} title={tooltip} aria-label={`Dispositor chain: ${tooltip}`}>
            {domAnchor ? (
              <div className="flex items-center gap-2 text-xs">
                {chip(anchor)}
                <span className="ml-1 uppercase text-[10px] px-1 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">dom</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-xs flex-wrap">
                {chain.map((nm, i) => (
                  <React.Fragment key={`${anchor}-${nm}-${i}`}>
                    {chip(nm)}
                    {i < chain.length - 1 && <span className="text-zinc-400">→</span>}
                  </React.Fragment>
                ))}
                {domFinal && (
                  <span className="ml-1 uppercase text-[10px] px-1 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">dom</span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const MORIN_PAYLOAD_KEYS = [
  'morin_aspects',
  'morin_antiscia',
  'morin_contra_antiscia',
  'morin_combustion',
  'morin_patterns',
];

function hasMorinRows(value) {
  if (Array.isArray(value)) return value.length > 0;
  if (value && typeof value === 'object') return Object.keys(value).length > 0;
  return false;
}

function hasMorinPayload(data) {
  if (!data || typeof data !== 'object') return false;
  return MORIN_PAYLOAD_KEYS.some((key) => hasMorinRows(data[key]));
}

function buildAstroClockChartSignature(data) {
  if (!data || typeof data !== 'object') return '';
  const timestamp = typeof data.timestamp === 'string' ? data.timestamp : '';
  const location = typeof data.location === 'string' ? data.location.trim().toLowerCase() : '';
  const timezone = typeof data.timezone === 'string' ? data.timezone.trim() : '';
  const houseCusps = Array.isArray(data.house_cusps)
    ? data.house_cusps.map((lon) => {
      const num = Number(lon);
      return Number.isFinite(num) ? num.toFixed(6) : '';
    }).join('|')
    : '';
  const planets = Array.isArray(data.planets)
    ? data.planets.map((planet) => {
      const lon = Number(planet?.longitude);
      const lonText = Number.isFinite(lon) ? lon.toFixed(6) : '';
      return `${planet?.planet || ''}:${lonText}:${planet?.house ?? ''}`;
    }).join('|')
    : '';
  if (!timestamp && !houseCusps && !planets) return '';
  return [timestamp, location, timezone, houseCusps, planets].join('||');
}

function preserveMorinPayloadForSameChart(currentData, nextData) {
  if (!currentData || !nextData) return nextData;
  if (!hasMorinPayload(currentData) || hasMorinPayload(nextData)) return nextData;
  const currentSignature = buildAstroClockChartSignature(currentData);
  const nextSignature = buildAstroClockChartSignature(nextData);
  if (!currentSignature || currentSignature !== nextSignature) return nextData;
  const merged = { ...nextData };
  for (const key of MORIN_PAYLOAD_KEYS) {
    merged[key] = currentData[key] ?? nextData[key];
  }
  return merged;
}


const AstroClock = ({ darkMode, setCurrentView, apiStatus, licenseActive=false }) => {
  const initialWarmStateRef = useRef(readAstroClockWarmState() || {});
  const initialWarmState = initialWarmStateRef.current;
  const [mode, setMode] = useState(() => initialWarmState.mode || 'realtime');
  const [manualDate, setManualDate] = useState(() => initialWarmState.manualDate || '');
  const [manualTime, setManualTime] = useState(() => initialWarmState.manualTime || '');
  const [manualLocation, setManualLocation] = useState(() => initialWarmState.manualLocation || '');
  const [activeSnapId, setActiveSnapId] = useState(() => initialWarmState.activeSnapId || '');
  const [data, setData] = useState(() => initialWarmState.data || null);
  const dataRef = useRef(initialWarmState.data || null);
  const [hours, setHours] = useState(() => initialWarmState.hours || null);
  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [clockLoadError, setClockLoadError] = useState('');
  const [includeModern, setIncludeModern] = useState(() => Boolean(initialWarmState.includeModern));
  const [houseSystem, setHouseSystem] = useState(() => {
    if (typeof initialWarmState.houseSystem === 'string' && initialWarmState.houseSystem.trim()) {
      return initialWarmState.houseSystem.trim();
    }
    try { return localStorage.getItem('vox_stella_house_system_code') || 'R'; } catch(_) { return 'R'; }
  });
  const [specialDegrees, setSpecialDegrees] = useState(() => (
    Array.isArray(initialWarmState.specialDegrees) ? initialWarmState.specialDegrees : []
  ));
  const [useMorin, setUseMorin] = useState(() => Boolean(initialWarmState.useMorin));
  const [activeManualIso, setActiveManualIso] = useState(() => initialWarmState.activeManualIso || null);
  const streamRef = useRef(null);
  const manualPending = mode === 'manual' && !activeManualIso;
  const [snaps, setSnaps] = useState(() => (
    Array.isArray(initialWarmState.snaps) ? initialWarmState.snaps : []
  ));
  const [loadingSnaps, setLoadingSnaps] = useState(false);
  const [snapsLoaded, setSnapsLoaded] = useState(() => Boolean(initialWarmState.snapsLoaded));
  const [showForensic, setShowForensic] = useState(false);
  const [openingForensic, setOpeningForensic] = useState(false);
  const [showTraits, setShowTraits] = useState(false);
  const [showSynastry, setShowSynastry] = useState(false);
  const [showTransits, setShowTransits] = useState(false);
  const [showElection, setShowElection] = useState(false);
  const [showAstrocartography, setShowAstrocartography] = useState(false);
  const [showResearch, setShowResearch] = useState(false);
  const [copiedCasePrompt, setCopiedCasePrompt] = useState(false);
  const [copiedBirthPrompt, setCopiedBirthPrompt] = useState(false);
  const [copiedAssetPrompt, setCopiedAssetPrompt] = useState(false);
  const [showAspectAnalysis, setShowAspectAnalysis] = useState(false);
  // Single-button prompt menu state
  const [showPromptMenu, setShowPromptMenu] = useState(false);
  // Name prompt modal state (works in dev and packaged builds)
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [namePromptType, setNamePromptType] = useState(null); // 'natal' | 'case' | 'asset'
  const [isStreaming, setIsStreaming] = useState(false);
  const featurePauseRef = useRef({ count: 0, resumeNeeded: false, snapshotIso: null, pausing: false, pausePromise: null });
  const modeRef = useRef(mode);
  const activeManualIsoRef = useRef(activeManualIso);
  const manualLocationRef = useRef(manualLocation);
  const viewVersionRef = useRef(0);
  const dashboardRequestRef = useRef(0);
  const hoursRequestRef = useRef(0);
  const loadingRef = useRef(false);
  const dashboardAbortRef = useRef(null);
  const hoursAbortRef = useRef(null);
  const skipNextManualDashboardRefreshRef = useRef(false);
  const skipNextRealtimeBootstrapRef = useRef(false);
  const skipNextHoursRefreshRef = useRef(false);

  const closeRealtimeStream = useCallback(() => {
    if (streamRef.current) {
      try { streamRef.current.close(); } catch (_) {}
      streamRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const replaceAbortController = useCallback((ref) => {
    if (ref.current) {
      try { ref.current.abort(); } catch (_) {}
    }
    const controller = new AbortController();
    ref.current = controller;
    return controller;
  }, []);

  useEffect(() => { modeRef.current = mode; }, [mode]);
  useEffect(() => { activeManualIsoRef.current = activeManualIso; }, [activeManualIso]);
  useEffect(() => { manualLocationRef.current = manualLocation; }, [manualLocation]);
  useEffect(() => { dataRef.current = data; }, [data]);
  useEffect(() => { loadingRef.current = loading; }, [loading]);
  useEffect(() => () => {
    if (dashboardAbortRef.current) {
      try { dashboardAbortRef.current.abort(); } catch (_) {}
      dashboardAbortRef.current = null;
    }
    if (hoursAbortRef.current) {
      try { hoursAbortRef.current.abort(); } catch (_) {}
      hoursAbortRef.current = null;
    }
  }, []);

  useEffect(() => {
    writeAstroClockWarmState({
      mode,
      manualDate,
      manualTime,
      manualLocation,
      activeSnapId,
      data,
      hours,
      includeModern,
      houseSystem,
      specialDegrees,
      useMorin,
      activeManualIso,
      snaps,
      snapsLoaded,
    });
  }, [
    activeManualIso,
    activeSnapId,
    data,
    hours,
    houseSystem,
    includeModern,
    manualDate,
    manualLocation,
    manualTime,
    mode,
    snaps,
    snapsLoaded,
    specialDegrees,
    useMorin,
  ]);

  const openNamePrompt = (type) => {
    setNamePromptType(type);
    setShowNamePrompt(true);
  };

  const buildActiveChartPromptPayload = () => {
    const live = data || {};
    return {
      chart_context: {
        mode: modeRef.current || mode,
        timestamp: live.timestamp || activeManualIsoRef.current || null,
        location: live.location || manualLocationRef.current || null,
        timezone: live.timezone || null,
        timezone_label: live.timezone_label || null,
        house_system: houseSystem || null,
      },
      display_toggles: {
        include_modern: !!includeModern,
        morin_mode: !!useMorin,
      },
      chart_factors: {
        planets: Array.isArray(live.planets) ? live.planets.map((p) => ({
          planet: p?.planet || null,
          sign: p?.sign || null,
          house: p?.house ?? null,
          longitude: p?.longitude ?? null,
          dignity_score: p?.dignity_score ?? null,
          essential_dignity: p?.essential_dignity ?? null,
          accidental_dignity: p?.accidental_dignity ?? null,
          retrograde: !!p?.retrograde,
        })) : [],
        moon: live.moon || null,
        moon_timeline: live.moon_timeline || null,
        solar_conditions: live.solar_conditions || null,
        top_aspects: Array.isArray(live.top_aspects) ? live.top_aspects.slice(0, 12) : [],
        morin_aspects: Array.isArray(live.morin_aspects) ? live.morin_aspects.slice(0, 12) : [],
        house_cusps: Array.isArray(live.house_cusps) ? live.house_cusps : [],
        house_rulers: live.house_rulers || {},
        receptions: live.receptions || null,
        fixed_star_hits: Array.isArray(live.fixed_star_hits) ? live.fixed_star_hits : [],
        arabic_parts: live.arabic_parts || {},
        dispositors: live.dispositors || {},
        sect: live.sect || null,
        special_degrees: Array.isArray(specialDegrees) ? specialDegrees : [],
        morin_patterns: live.morin_patterns || null,
        metrics: live.metrics || null,
      },
    };
  };

  const withActiveChartPromptPayload = (baseText) => {
    const payload = buildActiveChartPromptPayload();
    return `${baseText}\n\nCurrent Astro Clock chart payload:\n\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\``;
  };

  const buildCasePromptText = (name) => (
    withActiveChartPromptPayload(`Case name: ${name}\n\nTask:\nProvide the timestamp + location/time-zone package needed to cast forensic-astrology event charts. Do not generate charts or interpretations-only deliver items (1) and (2) below. Make best-judgment choices and state assumptions briefly (no follow-up questions).\n\n1) Identify Event Timestamps\n   - Primary: the earliest reliable discovery/notification moment.\n   - Alternates: (a) emergency/official log time, (b) legal pronouncement (e.g., time of death), (c) last confirmed alive/seen.\n   - For each timestamp: give local time (to the minute), UTC equivalent, a short reliability note, and 1–2 source links. If sources conflict, pick the most authoritative, explain why, and list the runner-up time(s).\n\n2) Locations & Time Zones\n   - For each timestamp: provide the full street address (venue + city + country), precise coordinates in decimal degrees (lat/long), time-zone name and UTC offset, and whether daylight saving time was in effect at that moment. Show the UTC conversion you used.\n\nOutput format (one markdown table):\nLabel | Local Time | UTC | Address | Lat/Long | Time Zone (incl. DST) | Source(s) | Reliability Notes`)
  );

  const buildNatalPromptText = (name) => (
    withActiveChartPromptPayload(`Subject: ${name}\n\nTask:\nProvide a complete natal birth data package to cast a birth chart. Do not generate the chart or interpretations-only deliver the data items below. Make best‑judgment choices and state assumptions briefly (no follow‑up questions).\n\n1) Birth Date & Time\n   - Local civil time (to the minute) with calendar (Gregorian/Julian if historical).\n   - UTC equivalent.\n   - Time accuracy rating (AA, A, B, C, DD) with a 1–2 sentence note.\n   - 1–2 source links (registry, certificate, biography, reliable database). If sources conflict, pick the most authoritative, explain why, and list runner‑up time(s).\n\n2) Location & Time Zone\n   - Birthplace: venue (if known), city, region, country.\n   - Coordinates in decimal degrees (lat/long).\n   - Time‑zone name and UTC offset at that moment; explicitly confirm whether DST was in effect.\n   - Show the UTC conversion used.\n\n3) If unknown/uncertain time\n   - Provide best estimated window (e.g., 08:00–10:00), basis (biography, hospital shift, sunrise/noon defaults), and cautions.\n\nOutput format (one markdown table):\nLabel | Local Time | UTC | Location | Lat/Long | Time Zone (incl. DST) | Source(s) | Reliability Notes`)
  );

  const buildAssetPromptText = (name) => (
    withActiveChartPromptPayload(`Asset/Instrument: ${name}\n\nTask:\nProvide a complete "birth chart" data package for this asset/instrument suitable for astrological research. Do not generate the chart or interpretations — only deliver the data items below. Make best‑judgment choices and state assumptions briefly (no follow‑up questions).\n\n1) Primary First‑Trade Chart\n   - Exchange/Market: primary listing venue (full name) and country.\n   - Ticker/Symbol: include class/series if applicable.\n   - First trade local time (to the minute) and date; specify whether this is opening auction/cross time or the first executed trade print.\n   - UTC equivalent.\n   - Location: exchange city/region/country; coordinates in decimal degrees (lat/long).\n   - Time‑zone name and UTC offset at that moment; explicitly confirm whether DST was in effect.\n   - 1–2 authoritative source links (exchange notices, prospectus/SEC/FCA filings, exchange/issuer press releases, reliable financial databases). If sources conflict, pick the most authoritative, explain why, and list runner‑up time(s).\n\n2) Special Cases Guidance\n   - Crypto: use genesis/launch timestamp or first exchange listing/trade; name the chain/exchange.\n   - Indices: use official launch/first publication timestamp.\n   - Futures/Options: use first trade timestamp on the primary exchange for the contract; include contract identifier.\n   - ETFs/ETNs: first trade on primary listing exchange; include ISIN if available.\n\nOutput format (one markdown table):\nLabel | Local Time | UTC | Exchange/Market | Ticker | Location | Lat/Long | Time Zone (incl. DST) | Source(s) | Reliability Notes`)
  );

  // Cusp Aspects filters (curated UI)
  const ANGULAR_SET = useMemo(()=> new Set(['H1','H4','H7','H10']), []);
  const SUCCEDENT_SET = useMemo(()=> new Set(['H2','H5','H8','H11']), []);
  const CADENT_SET = useMemo(()=> new Set(['H3','H6','H9','H12']), []);
  const REL_SET = useMemo(()=> new Set(['H5','H7','H11']), []);
  const TRAVEL_SET = useMemo(()=> new Set(['H3','H9']), []);
  const MONEY_SET = useMemo(()=> new Set(['H2','H8']), []);

  const DEFAULT_ALL = useMemo(()=> new Set(Array.from({length:12}, (_,i)=>`H${i+1}`)), []);
  const [cuspSelected, setCuspSelected] = useState(()=>{
    try { const raw = localStorage.getItem('cusp_sel'); if (raw) return new Set(JSON.parse(raw)); } catch(_) {}
    return new Set(DEFAULT_ALL);
  });
  const [cuspAll, setCuspAll] = useState(false);
  const [cuspAspectMode, setCuspAspectMode] = useState(()=>{ try { return localStorage.getItem('cusp_amode')||'all'; } catch(_) { return 'all'; }}); // 'hard'|'all'|'conj'
  const [cuspPhase, setCuspPhase] = useState(()=>{ try { return localStorage.getItem('cusp_phase')||'any'; } catch(_) { return 'any'; }}); // 'any'|'applying'|'separating'
  // Fixed orb policy for cusps: ≤ 1.0° (no UI slider)
  const [showCuspMenu, setShowCuspMenu] = useState(false);

  useEffect(()=>{ try { localStorage.setItem('cusp_sel', JSON.stringify(Array.from(cuspSelected))); } catch(_){} }, [cuspSelected]);
  useEffect(()=>{ try { localStorage.setItem('cusp_amode', String(cuspAspectMode)); } catch(_){} }, [cuspAspectMode]);
  useEffect(()=>{ try { localStorage.setItem('cusp_phase', String(cuspPhase)); } catch(_){} }, [cuspPhase]);
  // No cusp orb persistence; fixed at 1.0°

  const applyPreset = (set) => {
    setCuspSelected(prev => new Set([...prev, ...set]));
    setCuspAll(false);
  };
  const setAllCusps = () => { setCuspSelected(new Set(DEFAULT_ALL)); setCuspAll(true); };
  const clearCusps = () => { setCuspSelected(new Set()); setCuspAll(false); };
  const toggleCusp = (k) => {
    setCuspSelected(prev => { const n = new Set(prev); if (n.has(k)) n.delete(k); else n.add(k); setCuspAll(n.size===12); return n; });
  };

  const handleNamePromptSubmit = async (name) => {
    const trimmed = (name || '').trim();
    if (!trimmed) return;
    try {
      if (namePromptType === 'case') {
        const txt = buildCasePromptText(trimmed);
        const ok = await safeCopyText(txt);
        if (ok) { setCopiedCasePrompt(true); setTimeout(() => setCopiedCasePrompt(false), 2000); }
      } else if (namePromptType === 'natal') {
        const txt = buildNatalPromptText(trimmed);
        const ok = await safeCopyText(txt);
        if (ok) { setCopiedBirthPrompt(true); setTimeout(() => setCopiedBirthPrompt(false), 2000); }
      } else if (namePromptType === 'asset') {
        const txt = buildAssetPromptText(trimmed);
        const ok = await safeCopyText(txt);
        if (ok) { setCopiedAssetPrompt(true); setTimeout(() => setCopiedAssetPrompt(false), 2000); }
      }
    } finally {
      setShowNamePrompt(false);
    }
  };

  const beginViewVersion = useCallback(() => {
    viewVersionRef.current += 1;
    return viewVersionRef.current;
  }, []);

  const syncManualSnapshotInputs = useCallback((iso, { location, timezone } = {}) => {
    if (!iso || typeof iso !== 'string') return;
    try {
      const d = new Date(iso);
      if (!Number.isFinite(d.getTime())) return;
      const tz = (typeof timezone === 'string' && timezone.trim()) ? timezone.trim() : undefined;
      if (tz && typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
        const parts = new Intl.DateTimeFormat('en-GB', {
          timeZone: tz,
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        }).formatToParts(d);
        const get = (t) => (parts.find(p => p.type === t)?.value || '').padStart(2, '0');
        const yyyy = parts.find(p => p.type === 'year')?.value || String(d.getFullYear());
        const mm = get('month');
        const dd = get('day');
        const hh = get('hour');
        const min = get('minute');
        setManualDate(`${yyyy}-${mm}-${dd}`);
        setManualTime(`${hh}:${min}`);
      } else {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const hh = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        setManualDate(`${yyyy}-${mm}-${dd}`);
        setManualTime(`${hh}:${min}`);
      }
    } catch (_) {}
    if (typeof location === 'string' && location.trim()) {
      const nextLocation = location.trim();
      manualLocationRef.current = nextLocation;
      setManualLocation(nextLocation);
    }
  }, []);

  const normalizeSnapLocationKey = useCallback((value) => {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ');
  }, []);

  const findMatchingSnapId = useCallback((items, { iso, location } = {}) => {
    const targetMs = new Date(String(iso || '')).getTime();
    if (!Number.isFinite(targetMs)) return '';
    const targetLocation = normalizeSnapLocationKey(location);
    const findBy = (matcher) => {
      const match = (Array.isArray(items) ? items : []).find((snap) => {
        const snapMs = new Date(String(snap?.effective_datetime || '')).getTime();
        if (!Number.isFinite(snapMs) || snapMs !== targetMs) return false;
        return matcher(snap);
      });
      return match?.id ? String(match.id) : '';
    };
    const exactLocationMatch = targetLocation
      ? findBy((snap) => normalizeSnapLocationKey(snap?.location) === targetLocation)
      : '';
    if (exactLocationMatch) return exactLocationMatch;
    return findBy(() => true);
  }, [normalizeSnapLocationKey]);

  const applyDashboardPayload = useCallback((payload, options = {}) => {
    const transformed = transformDashboard(payload);
    const merged = options?.requestedMorin
      ? transformed
      : preserveMorinPayloadForSameChart(dataRef.current, transformed);
    dataRef.current = merged;
    setData(merged);
    if (!manualLocationRef.current && merged?.location) {
      manualLocationRef.current = merged.location;
      setManualLocation(merged.location);
    }
    return merged;
  }, []);

  const buildClockContext = useCallback((overrides = {}) => {
    const currentMode = modeRef.current || mode;
    const requestedMode = overrides.mode || currentMode;
    const hasExplicitLocation = typeof overrides.location === 'string' && overrides.location.trim();
    const hasExplicitTimezone = typeof overrides.timezone === 'string' && overrides.timezone.trim();
    const appliedTimezone = resolveAstroClockTimezone(data?.timezone, data?.timezone_label);
    const appliedLocation =
      (typeof data?.location === 'string' && data.location.trim()) ? data.location.trim() : undefined;
    const typedLocation =
      (typeof manualLocationRef.current === 'string' && manualLocationRef.current.trim())
        ? manualLocationRef.current.trim()
        : undefined;
    const locationDiffersFromApplied =
      !!typedLocation && !!appliedLocation && typedLocation.toLowerCase() !== appliedLocation.toLowerCase();
    const resolvedDatetime =
      (typeof overrides.datetime === 'string' && overrides.datetime.trim())
        ? overrides.datetime.trim()
        : activeManualIsoRef.current;
    const resolvedHouseSystem = overrides.houseSystem || houseSystem;
    const context = {};
    if (requestedMode === 'manual' && resolvedDatetime) {
      const resolvedLocation =
        (typeof overrides.location === 'string' && overrides.location.trim())
          ? overrides.location.trim()
          : typedLocation || appliedLocation;
      const resolvedTimezone =
        hasExplicitTimezone
          ? overrides.timezone.trim()
          : (hasExplicitLocation || locationDiffersFromApplied)
            ? undefined
            : appliedTimezone;
      context.mode = 'manual';
      context.datetime = resolvedDatetime;
      if (resolvedLocation) context.location = resolvedLocation;
      if (resolvedTimezone) context.timezone = resolvedTimezone;
    } else if (requestedMode === 'realtime') {
      const switchingToRealtime = currentMode !== 'realtime';
      const resolvedLocation =
        (typeof overrides.location === 'string' && overrides.location.trim())
          ? overrides.location.trim()
          : (switchingToRealtime ? undefined : appliedLocation);
      const resolvedTimezone =
        hasExplicitTimezone
          ? overrides.timezone.trim()
          : (switchingToRealtime ? undefined : appliedTimezone);
      context.mode = 'realtime';
      if (resolvedLocation) context.location = resolvedLocation;
      if (resolvedTimezone) context.timezone = resolvedTimezone;
    }
    if (resolvedHouseSystem) context.houseSystem = resolvedHouseSystem;
    return context;
  }, [data?.location, data?.timezone, data?.timezone_label, houseSystem, mode]);

  const deriveChartDateTimeParts = useCallback((iso, timezone) => {
    if (!iso || typeof iso !== 'string') return { date: '', time: '' };
    try {
      const d = new Date(iso);
      if (!Number.isFinite(d.getTime())) return { date: '', time: '' };
      const tz = (typeof timezone === 'string' && timezone.trim()) ? timezone.trim() : undefined;
      if (tz && typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
        const parts = new Intl.DateTimeFormat('en-GB', {
          timeZone: tz,
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        }).formatToParts(d);
        const get = (type) => (parts.find((part) => part.type === type)?.value || '').padStart(2, '0');
        const yyyy = parts.find((part) => part.type === 'year')?.value || String(d.getFullYear());
        const mm = get('month');
        const dd = get('day');
        const hh = get('hour');
        const min = get('minute');
        return { date: `${yyyy}-${mm}-${dd}`, time: `${hh}:${min}` };
      }
      return {
        date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
        time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
      };
    } catch (_) {
      return { date: '', time: '' };
    }
  }, []);

  const inferredActiveSnapId = useMemo(() => {
    if (activeSnapId) return '';
    return findMatchingSnapId(snaps, {
      iso: activeManualIso || data?.timestamp || '',
      location: manualLocation || data?.location || '',
    });
  }, [
    activeManualIso,
    activeSnapId,
    data?.location,
    data?.timestamp,
    findMatchingSnapId,
    manualLocation,
    snaps,
  ]);

  useEffect(() => {
    if (!activeSnapId && inferredActiveSnapId) {
      setActiveSnapId(inferredActiveSnapId);
    }
  }, [activeSnapId, inferredActiveSnapId]);

  const activeTransitSeed = useMemo(() => {
    const timezone = resolveAstroClockTimezone(data?.timezone, data?.timezone_label) || '';
    const activeIso = activeManualIso || data?.timestamp || '';
    const derived = deriveChartDateTimeParts(activeIso, timezone);
    return {
      snapId: activeSnapId || inferredActiveSnapId || '',
      date: manualDate || derived.date || '',
      time: manualTime || derived.time || '',
      location: (manualLocation || data?.location || '').trim(),
      timezone,
      houseSystem,
    };
  }, [
    activeManualIso,
    activeSnapId,
    data?.location,
    data?.timestamp,
    data?.timezone,
    data?.timezone_label,
    deriveChartDateTimeParts,
    inferredActiveSnapId,
    houseSystem,
    manualDate,
    manualLocation,
    manualTime,
  ]);

  const requestDashboard = useCallback(async (opts = {}, meta = {}) => {
    const requestId = ++dashboardRequestRef.current;
    const viewVersion = meta.viewVersion ?? viewVersionRef.current;
    const controller = replaceAbortController(dashboardAbortRef);
    const isCurrentRequest = () => shouldApplyAstroClockRequest({
      requestId,
      latestRequestId: dashboardRequestRef.current,
      viewVersion,
      latestViewVersion: viewVersionRef.current,
    });
    try {
      const res = await AstroClockAPI.getDashboard({ ...opts, signal: controller.signal });
      if (!res?.success) {
        if (isCurrentRequest()) {
          const message = getActionErrorMessage(
            { message: res?.error || res?.detail || res?.message },
            'Failed to load Astro Clock dashboard.',
          );
          console.error('Failed to load Astro Clock dashboard', res);
          setClockLoadError(message);
        }
        return null;
      }
      if (!isCurrentRequest()) {
        return null;
      }
      setClockLoadError('');
      return applyDashboardPayload(res.data, { requestedMorin: Boolean(opts?.morin) });
    } catch (error) {
      if (controller.signal.aborted) {
        return null;
      }
      if (isCurrentRequest()) {
        const message = getClockLoadErrorMessage(error, 'Failed to load Astro Clock dashboard.');
        console.error('Failed to load Astro Clock dashboard', error);
        setClockLoadError(message);
      }
      return null;
    } finally {
      if (dashboardAbortRef.current === controller) {
        dashboardAbortRef.current = null;
      }
    }
  }, [applyDashboardPayload, replaceAbortController]);

  const requestHours = useCallback(async (opts, meta = {}) => {
    const requestId = ++hoursRequestRef.current;
    const viewVersion = meta.viewVersion ?? viewVersionRef.current;
    const controller = replaceAbortController(hoursAbortRef);
    try {
      const res = await AstroClockAPI.getPlanetaryHours({ ...opts, signal: controller.signal });
      if (!res?.success) return null;
      if (!shouldApplyAstroClockRequest({
        requestId,
        latestRequestId: hoursRequestRef.current,
        viewVersion,
        latestViewVersion: viewVersionRef.current,
      })) {
        return null;
      }
      setHours(res.data);
      return res.data;
    } catch (error) {
      if (controller.signal.aborted) {
        return null;
      }
      if (shouldApplyAstroClockRequest({
        requestId,
        latestRequestId: hoursRequestRef.current,
        viewVersion,
        latestViewVersion: viewVersionRef.current,
      })) {
        console.error('Failed to load Astro Clock planetary hours', error);
      }
      return null;
    } finally {
      if (hoursAbortRef.current === controller) {
        hoursAbortRef.current = null;
      }
    }
  }, [replaceAbortController]);

  const syncClockModeAndRefresh = useCallback(async (context, meta = {}) => {
    const viewVersion = meta.viewVersion ?? viewVersionRef.current;
    const requestedSpecialDegrees = Array.isArray(meta.specialDegrees)
      ? meta.specialDegrees
      : specialDegrees;
    const requestedMorin = meta.morin ?? useMorin;
    setClockLoadError('');
    await AstroClockAPI.setMode(context);
    const [nextDashboard, nextHours] = await Promise.all([
      requestDashboard({
        includeModern,
        specialDegrees: requestedSpecialDegrees,
        morin: requestedMorin,
        ...context,
      }, { viewVersion }),
      requestHours(context, { viewVersion }),
    ]);
    return { dashboard: nextDashboard, hours: nextHours };
  }, [includeModern, requestDashboard, requestHours, specialDegrees, useMorin]);

  const refreshDashboard = async () => {
    setClockLoadError('');
    await requestDashboard({ includeModern, specialDegrees, morin: useMorin, ...buildClockContext() });
  };

  const cardBg = darkMode ? 'bg-gray-800/60 border-gray-700' : 'bg-white/60 border-white/80';
  const isProd = (import.meta && import.meta.env && import.meta.env.PROD) || false;
  const packagedRuntime = typeof window !== 'undefined' && window.IS_PACKAGED === true;
  const shouldRedirectToUpgrade = useCallback(() => shouldGatePremiumFeature({
    packagedRuntime,
    licenseActive,
  }), [packagedRuntime, licenseActive]);

  const handleCopyForensicCasePrompt = () => openNamePrompt('case');

  const handleCopyBirthChartPrompt = () => openNamePrompt('natal');

  const handleCopyAssetPrompt = () => openNamePrompt('asset');

  // Derived state for unified prompt button "Copied" feedback
  const anyPromptCopied = copiedBirthPrompt || copiedCasePrompt || copiedAssetPrompt;

  const handleOpenResearch = () => {
    // Dev only: ignore in prod
    if (isProd) return;
    setShowResearch(true);
  };

  const refreshSnaps = async ({ silent = false } = {}) => {
    setLoadingSnaps(true);
    if (!silent) setActionError('');
    try {
      const res = await AstroClockAPI.listSnaps();
      if (res?.success) {
        setSnaps(res.items || []);
        setSnapsLoaded(true);
      }
    } catch (error) {
      console.error('Failed to load Astro Clock snaps', error);
      if (!silent) {
        setActionError(getActionErrorMessage(error, 'Failed to load Astro Clock snaps.'));
      }
    }
    finally { setLoadingSnaps(false); }
  };

  // Polling or SSE (realtime only; disabled while manual is pending)
  useEffect(() => {
    let cancelled = false;
    let pollId = null;
    let reconnectTimerId = null;
    let realtimeFetchInFlight = false;
    let queuedRealtimeFetch = false;
    const viewVersion = viewVersionRef.current;
    const skipBootstrap = skipNextRealtimeBootstrapRef.current;
    if (skipBootstrap) {
      skipNextRealtimeBootstrapRef.current = false;
    }
    // Close any existing stream if leaving realtime or awaiting manual input
    if (mode !== 'realtime' || manualPending) {
      closeRealtimeStream();
      return () => {};
    }
    const clearReconnectTimer = () => {
      if (reconnectTimerId) {
        clearTimeout(reconnectTimerId);
        reconnectTimerId = null;
      }
    };
    const stopPolling = () => {
      if (pollId) {
        clearInterval(pollId);
        pollId = null;
      }
    };
    const fetchRealtimeDashboard = async () => {
      if (cancelled || modeRef.current !== 'realtime' || manualPending) return;
      if (realtimeFetchInFlight) {
        queuedRealtimeFetch = true;
        return;
      }
      realtimeFetchInFlight = true;
      try {
        await requestDashboard(
          { includeModern, specialDegrees, morin: useMorin, ...buildClockContext({ mode: 'realtime' }) },
          { viewVersion },
        );
      } finally {
        realtimeFetchInFlight = false;
        if (!cancelled && queuedRealtimeFetch && modeRef.current === 'realtime' && !manualPending) {
          queuedRealtimeFetch = false;
          void fetchRealtimeDashboard();
        }
      }
    };
    const startRealtimeTransport = async () => {
      if (cancelled || modeRef.current !== 'realtime' || manualPending) return;
      clearReconnectTimer();
      stopPolling();
      closeRealtimeStream();
      // SSE disabled when special degrees are in use; fallback to polling
      if (specialDegrees && specialDegrees.length === 0 && !useMorin) {
        const es = await AstroClockAPI.createStream({ includeModern });
        if (cancelled || modeRef.current !== 'realtime' || manualPending) {
          try { es?.close?.(); } catch (_) {}
          return;
        }
        if (es) {
          streamRef.current = es;
          setIsStreaming(true);
          es.onmessage = () => { void fetchRealtimeDashboard(); };
          es.onerror = () => {
            if (streamRef.current === es) {
              try { es.close(); } catch (_) {}
              streamRef.current = null;
            }
            setIsStreaming(false);
            if (cancelled || modeRef.current !== 'realtime' || manualPending) return;
            clearReconnectTimer();
            reconnectTimerId = setTimeout(() => {
              reconnectTimerId = null;
              void startRealtimeTransport();
            }, 1000);
          };
          return;
        }
      }
      pollId = setInterval(() => {
        void fetchRealtimeDashboard();
      }, 10000);
    };
    // Avoid clearing data on entry; prevents visible flicker while the first fetch completes
    const start = async () => {
      if (!skipBootstrap) {
        // Ensure backend is in realtime mode before streaming/fetching
        try { await AstroClockAPI.setMode({ mode: 'realtime', houseSystem }); } catch(_){}
        if (cancelled) return;
        // Get the first dashboard payload on screen before starting secondary realtime plumbing.
        await fetchRealtimeDashboard();
        if (cancelled) return;
      }
      await startRealtimeTransport();
    };
    void start();
    return () => {
      cancelled = true;
      clearReconnectTimer();
      stopPolling();
      closeRealtimeStream();
    };
  }, [buildClockContext, closeRealtimeStream, includeModern, houseSystem, specialDegrees, mode, manualPending, requestDashboard, useMorin]);

  // Manual mode: refresh dashboard when includeModern toggles
  useEffect(() => {
    if (mode !== 'manual' || manualPending) return;
    if (skipNextManualDashboardRefreshRef.current) {
      skipNextManualDashboardRefreshRef.current = false;
      return;
    }
    (async () => {
      await requestDashboard({ includeModern, specialDegrees, morin: useMorin, ...buildClockContext({ mode: 'manual' }) });
    })();
  }, [buildClockContext, includeModern, specialDegrees, mode, manualPending, requestDashboard, useMorin]);

  // Load planetary hours and keep in sync with stream payload when present; fallback to periodic refresh
  useEffect(() => {
    if (manualPending) return;
    if (mode === 'manual' && !activeManualIso) return;
    let cancelled = false;
    const viewVersion = viewVersionRef.current;
    const fetchHours = async () => {
      if (cancelled) return;
      await requestHours(buildClockContext(), { viewVersion });
    };
    if (skipNextHoursRefreshRef.current) {
      skipNextHoursRefreshRef.current = false;
    } else {
      fetchHours();
    }
    const id = setInterval(fetchHours, 60000);
    return () => { cancelled = true; clearInterval(id); };
  }, [activeManualIso, buildClockContext, manualPending, mode, requestHours]);

  useEffect(() => {
    if (!activeManualIso || (manualDate && manualTime)) return;
    syncManualSnapshotInputs(activeManualIso, {
      location: data?.location || manualLocationRef.current,
      timezone: resolveAstroClockTimezone(data?.timezone, data?.timezone_label),
    });
  }, [activeManualIso, data?.location, data?.timezone, data?.timezone_label, manualDate, manualTime, syncManualSnapshotInputs]);

  useEffect(() => {
    if (mode !== 'realtime' || manualPending || !data?.timestamp) return;
    syncManualSnapshotInputs(data.timestamp, {
      location: data?.location || manualLocationRef.current,
      timezone: resolveAstroClockTimezone(data?.timezone, data?.timezone_label),
    });
  }, [mode, manualPending, data?.timestamp, data?.location, data?.timezone, data?.timezone_label, syncManualSnapshotInputs]);

  // When stream payload includes planetary_hours, use it
  useEffect(() => {
    if (data?.planetary_hours) {
      setHours(data.planetary_hours);
    }
  }, [data?.planetary_hours]);

  const applyManual = async () => {
    if (!manualDate || !manualTime || loadingRef.current) return;
    setLoading(true);
    setActionError('');
    try {
      setActiveSnapId('');
      const viewVersion = beginViewVersion();
      const iso = `${manualDate}T${manualTime}:00`;
      const manualContext = buildClockContext({
        mode: 'manual',
        datetime: iso,
        location: manualLocation || data?.location || 'Greenwich, UK',
      });
      closeRealtimeStream();
      skipNextManualDashboardRefreshRef.current = true;
      skipNextHoursRefreshRef.current = true;
      modeRef.current = 'manual';
      activeManualIsoRef.current = iso;
      setMode('manual');
      setActiveManualIso(iso);
      await syncClockModeAndRefresh(manualContext, { viewVersion });
    } catch (error) {
      console.error('Failed to apply Astro Clock manual mode', error);
      setActionError(getActionErrorMessage(error, 'Failed to switch Astro Clock into manual mode.'));
      throw error;
    } finally { setLoading(false); }
  };

  // Jump the main clock to a specific ISO timestamp (from Transits modal)
  const jumpToIso = useCallback(async (arg) => {
    const payload = (arg && typeof arg === 'object') ? arg : { iso: arg };
    const iso = payload.iso;
    if (!iso || typeof iso !== 'string' || loadingRef.current) return;
    setLoading(true);
    setActionError('');
    try {
      setActiveSnapId('');
      const viewVersion = beginViewVersion();
      // If election provided a specific location/timezone, honor them
      const jumpLocation = (typeof payload.location === 'string' && payload.location.trim()) ? payload.location.trim() : (manualLocation || 'Greenwich, UK');
      const jumpTimezone = (typeof payload.timezone === 'string' && payload.timezone.trim()) ? payload.timezone.trim() : undefined;
      const manualContext = buildClockContext({
        mode: 'manual',
        datetime: iso,
        location: jumpLocation,
        timezone: jumpTimezone,
      });
      syncManualSnapshotInputs(iso, { location: jumpLocation, timezone: jumpTimezone });
      closeRealtimeStream();
      skipNextManualDashboardRefreshRef.current = true;
      skipNextHoursRefreshRef.current = true;
      modeRef.current = 'manual';
      activeManualIsoRef.current = iso;
      setMode('manual');
      setActiveManualIso(iso);
      await syncClockModeAndRefresh(manualContext, { viewVersion });
    } catch (error) {
      console.error('Failed to jump Astro Clock to manual snapshot', error);
      setActionError(getActionErrorMessage(error, 'Failed to switch Astro Clock into manual mode.'));
      throw error;
    } finally {
      setLoading(false);
    }
  }, [beginViewVersion, buildClockContext, closeRealtimeStream, manualLocation, syncClockModeAndRefresh, syncManualSnapshotInputs]);

  const resumeRealtime = useCallback(async () => {
    if (loadingRef.current) return;
    setLoading(true);
    const ref = featurePauseRef.current;
    let success = false;
    const viewVersion = beginViewVersion();
    // Ensure UI state moves to realtime even if network requests fail
    modeRef.current = 'realtime';
    activeManualIsoRef.current = null;
    setActiveSnapId('');
    setMode('realtime');
    setActiveManualIso(null);
    try {
      const realtimeContext = buildClockContext({ mode: 'realtime' });
      skipNextRealtimeBootstrapRef.current = true;
      skipNextHoursRefreshRef.current = true;
      const { dashboard: nextDashboard } = await syncClockModeAndRefresh(realtimeContext, { viewVersion });
      if (nextDashboard?.timestamp) {
        syncManualSnapshotInputs(nextDashboard.timestamp, {
          location: nextDashboard.location,
          timezone: resolveAstroClockTimezone(nextDashboard.timezone, nextDashboard.timezone_label),
        });
      }
      success = true;
    } finally {
      setLoading(false);
      if (success) {
        ref.resumeNeeded = false;
        ref.snapshotIso = null;
        ref.pausing = false;
        ref.pausePromise = null;
        if (ref.count !== 0) ref.count = 0;
      }
    }
  }, [beginViewVersion, buildClockContext, syncClockModeAndRefresh, syncManualSnapshotInputs]);

  const enterManualMode = useCallback(async () => {
    if (loadingRef.current) return;
    if (modeRef.current === 'manual' && !activeManualIsoRef.current) {
      return;
    }
    const target = resolveManualSnapshotTarget({
      activeManualIso: activeManualIsoRef.current,
      dataTimestamp: data?.timestamp,
      dataLocation: data?.location,
      manualLocation: manualLocationRef.current,
      timezone: data?.timezone,
      timezoneLabel: data?.timezone_label,
    });
    if (modeRef.current === 'manual' && activeManualIsoRef.current) {
      syncManualSnapshotInputs(target.iso, { location: target.location, timezone: target.timezone });
      return;
    }
    await jumpToIso(target);
  }, [data?.location, data?.timestamp, data?.timezone, data?.timezone_label, jumpToIso, syncManualSnapshotInputs]);

  const pauseRealtimeForFeature = useCallback(async () => {
    const ref = featurePauseRef.current;
    ref.count += 1;
    if (mode !== 'realtime') {
      return;
    }
    if (ref.resumeNeeded) {
      if (ref.pausePromise) {
        try { await ref.pausePromise; } catch (_) {}
      }
      return;
    }
    if (ref.pausing && ref.pausePromise) {
      try { await ref.pausePromise; } catch (_) {}
      return;
    }
    const snapshotIso = (data && data.timestamp) ? data.timestamp : new Date().toISOString();
    const snapshotLocation = (data && data.location) ? data.location : (manualLocation || 'Greenwich, UK');
    ref.pausing = true;
    ref.snapshotIso = null;
    ref.pausePromise = (async () => {
      try {
        await jumpToIso({ iso: snapshotIso, location: snapshotLocation });
        ref.resumeNeeded = true;
        ref.snapshotIso = snapshotIso;
      } finally {
        ref.pausing = false;
        ref.pausePromise = null;
      }
    })();
    try {
      await ref.pausePromise;
    } catch (err) {
      console.error('Failed to pause realtime for feature', err);
    }
  }, [mode, data, manualLocation, jumpToIso]);

  const resumeRealtimeAfterFeature = useCallback(async () => {
    const ref = featurePauseRef.current;
    if (ref.count > 0) {
      ref.count -= 1;
    }
    if (ref.count > 0) {
      return;
    }
    if (ref.pausePromise) {
      try { await ref.pausePromise; } catch (_) {}
    }
    if (!ref.resumeNeeded) {
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
      return;
    }
    const snapshotIso = ref.snapshotIso;
    if (mode !== 'manual') {
      ref.resumeNeeded = false;
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
      return;
    }
    if (snapshotIso && activeManualIso && snapshotIso !== activeManualIso) {
      ref.resumeNeeded = false;
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
      return;
    }
    try {
      await resumeRealtime();
    } catch (err) {
      console.error('Failed to resume realtime after feature', err);
    } finally {
      ref.resumeNeeded = false;
      ref.snapshotIso = null;
      ref.pausePromise = null;
      ref.pausing = false;
    }
  }, [mode, activeManualIso, resumeRealtime]);

  const handleOpenForensic = useCallback(async () => {
    if (shouldRedirectToUpgrade()) {
      redirectToPremiumUpgrade(window.electronAPI?.openExternal);
      return;
    }
    setOpeningForensic(true);
    try {
      await pauseRealtimeForFeature();
    } catch (err) {
      console.error('Failed to pause realtime for forensic view', err);
    } finally {
      setOpeningForensic(false);
      setShowForensic(true);
    }
  }, [pauseRealtimeForFeature, shouldRedirectToUpgrade]);

  const handleCloseForensic = useCallback(() => {
    setOpeningForensic(false);
    setShowForensic(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after forensic view', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenTraitProfile = useCallback(async () => {
    if (shouldRedirectToUpgrade()) {
      redirectToPremiumUpgrade(window.electronAPI?.openExternal);
      return;
    }
    try {
      await pauseRealtimeForFeature();
    } catch (err) {
      console.error('Failed to pause realtime for trait profile', err);
    } finally {
      setShowTraits(true);
    }
  }, [pauseRealtimeForFeature, shouldRedirectToUpgrade]);

  const handleCloseTraitProfile = useCallback(() => {
    setShowTraits(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after trait profile', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenSynastry = useCallback(async () => {
    if (shouldRedirectToUpgrade()) {
      redirectToPremiumUpgrade(window.electronAPI?.openExternal);
      return;
    }
    try {
      await pauseRealtimeForFeature();
    } catch (err) {
      console.error('Failed to pause realtime for synastry', err);
    } finally {
      setShowSynastry(true);
    }
  }, [pauseRealtimeForFeature, shouldRedirectToUpgrade]);

  const handleCloseSynastry = useCallback(() => {
    setShowSynastry(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after synastry', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenTransits = useCallback(() => {
    if (shouldRedirectToUpgrade()) {
      redirectToPremiumUpgrade(window.electronAPI?.openExternal);
      return;
    }
    setShowTransits(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for transits', err); });
  }, [pauseRealtimeForFeature, shouldRedirectToUpgrade]);

  const handleCloseTransits = useCallback(() => {
    setShowTransits(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after transits', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenElection = useCallback(() => {
    if (shouldRedirectToUpgrade()) {
      redirectToPremiumUpgrade(window.electronAPI?.openExternal);
      return;
    }
    setShowElection(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for election scanner', err); });
  }, [pauseRealtimeForFeature, shouldRedirectToUpgrade]);

  const handleCloseElection = useCallback(() => {
    setShowElection(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after election scanner', err); });
  }, [resumeRealtimeAfterFeature]);

  const handleOpenAstrocartography = useCallback(() => {
    if (shouldRedirectToUpgrade()) {
      redirectToPremiumUpgrade(window.electronAPI?.openExternal);
      return;
    }
    setShowAstrocartography(true);
    pauseRealtimeForFeature().catch((err) => { console.error('Failed to pause realtime for astrocartography', err); });
  }, [pauseRealtimeForFeature, shouldRedirectToUpgrade]);

  const handleCloseAstrocartography = useCallback(() => {
    setShowAstrocartography(false);
    resumeRealtimeAfterFeature().catch((err) => { console.error('Failed to resume realtime after astrocartography', err); });
  }, [resumeRealtimeAfterFeature]);

  // Snap actions
  const doSnap = async () => {
    // Avoid window.prompt in packaged builds; generate a friendly default label
    const ts = data?.timestamp || new Date().toISOString();
    const loc = data?.location || manualLocation || '';
    const defaultLabel = `Snap ${ts.replace('T',' ').replace('Z','')}${loc? ` - ${loc}`:''}`;
    const label = defaultLabel;
    setActionError('');
    try {
      const res = await AstroClockAPI.createSnap({ label, includeModern, specialDegrees });
      const nextSnapId = String(res?.data?.id || res?.id || '');
      if (nextSnapId) setActiveSnapId(nextSnapId);
      await refreshSnaps();
      return {
        success: true,
        id: nextSnapId,
        label: String(res?.data?.label || label),
      };
    } catch (error) {
      console.error('Failed to create Astro Clock snap', error);
      const message = getActionErrorMessage(error, 'Failed to save this chart as a snap.');
      setActionError(message);
      return {
        success: false,
        error: message,
      };
    }
  };

  const handleChartLocationChange = useCallback(async (nextLocation) => {
    const location = String(nextLocation || '').trim();
    if (!location) return;
    setLoading(true);
    setActionError('');
    try {
      setActiveSnapId('');
      manualLocationRef.current = location;
      setManualLocation(location);
      const viewVersion = beginViewVersion();
      if (modeRef.current === 'manual' && activeManualIsoRef.current) {
        const manualContext = buildClockContext({
          mode: 'manual',
          datetime: activeManualIsoRef.current,
          location,
        });
        const { dashboard: nextDashboard } = await syncClockModeAndRefresh(manualContext, { viewVersion });
        syncManualSnapshotInputs(activeManualIsoRef.current, {
          location: nextDashboard?.location || location,
          timezone: resolveAstroClockTimezone(nextDashboard?.timezone, nextDashboard?.timezone_label) || manualContext.timezone,
        });
        return;
      }
      const realtimeContext = buildClockContext({
        mode: 'realtime',
        location,
      });
      await syncClockModeAndRefresh(realtimeContext, { viewVersion });
    } catch (error) {
      console.error('Failed to update Astro Clock chart location', error);
      setActionError(getActionErrorMessage(error, 'Failed to update the Astro Clock location.'));
      throw error;
    } finally {
      setLoading(false);
    }
  }, [beginViewVersion, buildClockContext, syncClockModeAndRefresh, syncManualSnapshotInputs]);

  const loadSnap = async (snap) => {
    if (!snap || loadingRef.current) return;
    const iso = snap.effective_datetime;
    const location = snap.location;
    setLoading(true);
    setActionError('');
    try {
      setActiveSnapId(String(snap.id || ''));
      const viewVersion = beginViewVersion();
      const nextSpecialDegrees = Array.isArray(snap.special_degrees) ? snap.special_degrees : specialDegrees;
      const snapTimezone = resolveAstroClockTimezone(
        snap?.dashboard?.timezone,
        snap?.dashboard?.timezone_label,
      );
      if (Array.isArray(snap.special_degrees)) setSpecialDegrees(snap.special_degrees);
      const manualContext = buildClockContext({
        mode: 'manual',
        datetime: iso,
        location,
      });
      syncManualSnapshotInputs(iso, { location, timezone: snapTimezone });
      closeRealtimeStream();
      skipNextManualDashboardRefreshRef.current = true;
      skipNextHoursRefreshRef.current = true;
      modeRef.current = 'manual';
      activeManualIsoRef.current = iso;
      setMode('manual');
      setActiveManualIso(iso);
      await syncClockModeAndRefresh(manualContext, {
        viewVersion,
        specialDegrees: nextSpecialDegrees,
      });
    } catch (error) {
      console.error('Failed to load Astro Clock snap', error);
      setActionError(getActionErrorMessage(error, 'Failed to load the selected snap.'));
      throw error;
    } finally { setLoading(false); }
  };

  const deleteSnap = async (id) => {
    setActionError('');
    try {
      await AstroClockAPI.deleteSnap(id);
      await refreshSnaps();
    } catch (error) {
      console.error('Failed to delete Astro Clock snap', error);
      setActionError(getActionErrorMessage(error, 'Failed to delete the selected snap.'));
    }
  };

  const handleHouseSystemChange = async (code) => {
    try {
      const viewVersion = beginViewVersion();
      setHouseSystem(code);
      try { localStorage.setItem('vox_stella_house_system_code', code); } catch(_) {}
      // Update backend engine setting according to current mode
      if (mode === 'manual') {
        // Manual mode requires datetime (and optional location)
        const iso = activeManualIso;
        if (!iso) {
          // If manual time isn’t set yet, skip engine update; UI will apply when time is set
        } else {
          await AstroClockAPI.setMode(buildClockContext({
            mode: 'manual',
            datetime: iso,
            location: manualLocation || data?.location || 'Greenwich, UK',
            houseSystem: code,
          }));
        }
      } else {
        await AstroClockAPI.setMode(buildClockContext({ mode: 'realtime', houseSystem: code }));
      }
      // Refresh dashboard and hours
      const nextContext = buildClockContext({ houseSystem: code, mode: mode === 'manual' ? 'manual' : 'realtime' });
      await Promise.allSettled([
        requestDashboard({ includeModern, specialDegrees, morin: useMorin, ...nextContext }, { viewVersion }),
        requestHours(nextContext, { viewVersion }),
      ]);
    } catch(_) {}
  };

  useEffect(() => { refreshSnaps({ silent: true }); }, []);

  return (
    <div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8`}>
      <button onClick={() => setCurrentView('dashboard')} className="flex items-center text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 mb-4">
        <span className="mr-2">←</span> Back to Dashboard
      </button>
      {/* Removed page title per request */}

      {/* Controls */}
      <div className={`border rounded-2xl p-4 mb-6 ${cardBg}`}>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs mb-1">Mode</label>
            <div className="inline-flex rounded overflow-hidden border">
              <button
                onClick={resumeRealtime}
                disabled={loading}
                className={`px-3 py-1 text-sm disabled:opacity-60 disabled:cursor-not-allowed ${mode==='realtime'?'bg-blue-600 text-white':'bg-gray-200 dark:bg-gray-700'}`}
              >Realtime</button>
              <button
                onClick={enterManualMode}
                disabled={loading}
                className={`px-3 py-1 text-sm disabled:opacity-60 disabled:cursor-not-allowed ${mode==='manual'?'bg-blue-600 text-white':'bg-gray-200 dark:bg-gray-700'}`}
              >Manual</button>
            </div>
          </div>
          <div>
            <label className="block text-xs mb-1">Date</label>
            <input type="date" value={manualDate} onChange={e=>setManualDate(e.target.value)} className="px-3 py-1 border rounded" />
          </div>
          <div>
            <label className="block text-xs mb-1">Time</label>
            <input
              type="time"
              lang="en-GB"
              inputMode="numeric"
              step="60"
              placeholder="HH:MM"
              value={manualTime}
              onChange={e=>setManualTime(e.target.value)}
              className="px-3 py-1 border rounded"
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs mb-1">Location</label>
          <input
            type="text"
            placeholder="e.g., London, UK"
            value={manualLocation}
            onChange={e => {
              const nextLocation = e.target.value;
              manualLocationRef.current = nextLocation;
              setManualLocation(nextLocation);
            }}
            className="w-full px-3 py-1 border rounded"
          />
          </div>
          <button onClick={applyManual} disabled={loading || mode !== 'manual' || !manualDate || !manualTime} className="px-4 py-2 bg-gray-900 text-white rounded disabled:bg-gray-500">Apply</button>
          <button
            onClick={async()=>{
              setLoading(true);
              try {
                const activeContext = buildClockContext();
                setClockLoadError('');
                await Promise.allSettled([
                  requestDashboard({ includeModern, specialDegrees, morin: useMorin, ...activeContext }),
                  requestHours(activeContext),
                ]);
              } catch(_){}
              finally { setLoading(false); }
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded"
          >Refresh</button>
        </div>
        {actionError && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {actionError}
          </div>
        )}
        {!actionError && clockLoadError && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {clockLoadError}
          </div>
        )}
      </div>

      {/* 12-col layout, custom widths/rows on md+ */}
      <div className="grid gap-y-4 gap-x-4 lg:gap-y-6 lg:gap-x-5 md:grid-cols-[minmax(200px,0.78fr)_minmax(620px,2.55fr)_minmax(300px,1.22fr)] md:grid-rows-[auto_minmax(500px,auto)_auto]">
        {/* Left column (col 1): stack Dispositors + Fixed Stars together to avoid row stretching */}
        <div className="order-1 md:[grid-column:1] md:[grid-row:1/4] self-start space-y-4 lg:space-y-6">
          {/* Receptions - rectangle */}
          <section className={`${panelCls} h-auto max-h-80 md:max-h-[340px] overflow-auto`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Receptions</h3>
            </div>
            <ReceptionsTile dataTimestamp={data?.timestamp} receptions={data?.receptions} />
          </section>
          {/* G) Dispositors - rectangle */}
          <section className={`${panelCls} h-auto max-h-80 md:max-h-[340px] overflow-auto`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Dispositors</h3>
            </div>
            {!data && <div className="text-sm text-zinc-500">Loading…</div>}
          {data && <DispositorsCard data={data} includeModern={includeModern} />}
          </section>

          {/* H) Fixed Stars - square */}
          <section className={`${panelCls} aspect-square`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Fixed Stars</h3>
            </div>
            <div className="text-sm space-y-2 overflow-auto h-[calc(100%-28px)] pr-1">
              {data?.fixed_star_hits?.length ? data.fixed_star_hits.map((hit, idx)=> {
                const conjWith = (() => {
                  if (hit.target_type === 'planet') {
                    const glyph = PlanetSymbols[hit.target] || '';
                    return `conj with ${glyph ? glyph + ' ' : ''}${hit.target}`;
                  }
                  if (hit.target_type === 'cusp') {
                    const labelMap = { C1: 'Asc', C10: 'MC' };
                    const nice = labelMap[hit.target] || hit.target;
                    return `conj with ${nice}`;
                  }
                  return `conj with ${hit.target}`;
                })();
                const orbText = typeof hit.orb_deg === 'number' ? `${Number(hit.orb_deg).toFixed(2)}°` : `${hit.orb_deg}°`;
                return (
                  <div key={idx}>
                    <div className="flex justify-between">
                      <span>{hit.name}</span>
                      <span className="text-zinc-600">{hit.constellation} {degreeTextFromLon(hit.star_longitude)}</span>
                    </div>
                    <div className="text-xs text-zinc-500">{conjWith} ({orbText})</div>
                  </div>
                );
              }) : <div className="text-zinc-500">No close fixed stars</div>}
            </div>
          </section>

          {/* Arabic Lots - square */}
          <section className={`${panelCls} aspect-square`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Arabic Lots</h3>
              {/* Variant toggles: Death A/B, Poison V1/V2, Plane V1/V2 */}
            </div>
            <ArabicLotsPanel data={data} />
          </section>

          {/* Sect - square */}
          <section className={`${panelCls} aspect-square`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Sect</h3>
            </div>
            <div className="astro-scroll-shell h-[calc(100%-28px)]">
              <div className="astro-scroll text-sm space-y-2">
                <SectPanel data={data} />
              </div>
            </div>
          </section>

          {/* Degree Hits - square under Sect */}
          <section>
            <DegreeHitsTile
              metrics={data?.metrics}
              specialDegrees={specialDegrees}
              onApplyDegrees={(tokens)=> { setSpecialDegrees(tokens || []); }}
              onClearDegrees={()=> { setSpecialDegrees([]); }}
            />
          </section>
          <section>
            <AlmutenTile almutens={data?.almutens} />
          </section>
          {/* (Compass Bearings removed from left column per layout) */}

        </div>

          {/* (moved Current Cusps under Positions + Dignity in right column) */}

        {/* Center column (col 2) */}
        <div className="order-4 md:[grid-column:2] md:[grid-row:1] space-y-4 lg:space-y-6">
          {/* Action buttons row: Trait Profile, Forensic, Prompt menu */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
              onClick={handleOpenSynastry}
            >
              Synastry
            </button>
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
              onClick={handleOpenTraitProfile}
            >
              Trait Profile
            </button>
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
              onClick={handleOpenTransits}
            >
              Transits
            </button>
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
              onClick={handleOpenAstrocartography}
            >
              Astrocartography
            </button>
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
              onClick={handleOpenElection}
            >
              Election
            </button>
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
              onClick={handleOpenForensic}
            >
              Forensic
            </button>
            {/* Unified Prompt button with dropdown */}
            <div className="relative">
              <button
                type="button"
                className={`px-1.5 py-0.5 rounded-lg border text-[11px] transition-colors min-w-[120px]
                           ${anyPromptCopied
                             ? 'bg-gray-800 text-white border-gray-800'
                             : 'bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300 dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700'}`}
                onClick={()=> setShowPromptMenu(v=>!v)}
                title="Copy AI-ready prompt"
              >
                {anyPromptCopied ? 'Copied' : 'Copy Prompt ▾'}
              </button>
              {showPromptMenu && (
                <div className="absolute z-10 mt-1 w-56 rounded-lg border bg-white shadow p-2 text-[12px] dark:bg-gray-800 dark:border-gray-700">
                  <div className="px-2 pb-1 text-[11px] font-medium text-zinc-600 dark:text-zinc-300">Choose prompt type</div>
                  <button
                    type="button"
                    className="w-full text-left px-2 py-1 rounded hover:bg-zinc-100 dark:hover:bg-gray-700"
                    onClick={()=> { setShowPromptMenu(false); handleCopyBirthChartPrompt(); }}
                    title="Copy AI-ready natal data prompt"
                  >
                    Natal prompt (copy)
                  </button>
                  <button
                    type="button"
                    className="w-full text-left px-2 py-1 rounded hover:bg-zinc-100 dark:hover:bg-gray-700"
                    onClick={()=> { setShowPromptMenu(false); handleCopyForensicCasePrompt(); }}
                    title="Copy AI-ready case-gathering prompt"
                  >
                    Case prompt (copy)
                  </button>
                  <button
                    type="button"
                    className="w-full text-left px-2 py-1 rounded hover:bg-zinc-100 dark:hover:bg-gray-700"
                    onClick={()=> { setShowPromptMenu(false); handleCopyAssetPrompt(); }}
                    title="Copy AI-ready asset first-trade prompt"
                  >
                    Asset prompt (copy)
                  </button>
                </div>
              )}
            </div>
          </div>
          {/* A) Solar Conditions - rectangle with chips (Morin-aware) */}
          <section className={panelCls}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {!isProd && (
                  <button
                    type="button"
                    className="px-2 py-0.5 rounded border border-zinc-300 hover:bg-zinc-50 text-[11px]"
                    onClick={handleOpenResearch}
                    title="Open Research Mode (Dev)"
                  >
                    Research
                  </button>
                )}
                <h3 className="font-semibold text-sm">Solar Conditions</h3>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {useMorin ? (
                Array.isArray(data?.morin_combustion) && data.morin_combustion.length ? (
                  data.morin_combustion.map((it, idx) => (
                    <span key={`mc-${idx}`} className={`text-xs rounded-full px-2 py-1 border ${it.status==='cazimi'?'border-amber-300 bg-amber-50': it.status==='combust'?'border-rose-300 bg-rose-50': it.status==='under_beams'?'border-sky-300 bg-sky-50':'border-zinc-300 bg-zinc-50'}`} title={`${it.status} · ${Number(it.distance_deg||0).toFixed(2)}°`}>
                      <span className="mr-1">{PlanetSymbols[it.planet] || it.planet}</span>
                      {it.status.replace('_',' ')} · {Number(it.distance_deg||0).toFixed(2)}°
                    </span>
                  ))
                ) : <span className="text-xs text-zinc-500">No solar data (Morin)</span>
              ) : (
                ['cazimi','combustion','under_beams']
                  .flatMap(g => (data?.solar_conditions?.[g]||[]).map((it, idx)=> ({...it, group:g, idx: `${g}-${idx}`})))
                  .map(item => {
                    const label = (() => {
                      const base = item.group==='cazimi' ? 'Cazimi' : item.group==='combustion' ? 'Combust' : 'Under Beams';
                      if (item.group === 'combustion' && typeof item.phase === 'string' && item.phase) {
                        const ph = item.phase.charAt(0).toUpperCase() + item.phase.slice(1);
                        return `${base} (${ph})`;
                      }
                      if (item.group === 'under_beams' && typeof item.phase === 'string' && item.phase) {
                        const ph = item.phase.charAt(0).toUpperCase() + item.phase.slice(1);
                        return `${base} (${ph})`;
                      }
                      return base;
                    })();
                    const hours = (() => {
                      const t = Number(item.approx_hours_to_conjunction);
                      const s = Number(item.approx_hours_since_conjunction);
                      if (isFinite(t)) return `In ~${Math.round(t)}h`;
                      if (isFinite(s)) return `Since ~${Math.round(s)}h`;
                      return null;
                    })();
                    const title = [
                      (item.distance_from_sun!=null)? `Elongation: ${Number(item.distance_from_sun).toFixed(2)}°` : null,
                      (typeof item.relative_speed_deg_per_day === 'number') ? `Rel speed: ${item.relative_speed_deg_per_day.toFixed(2)}°/day` : null,
                      hours,
                    ].filter(Boolean).join(' • ');
                    return (
                      <span key={item.idx} className="text-xs rounded-full border border-zinc-200 bg-white px-2 py-1" title={title}>
                        <span className="mr-1">{PlanetSymbols[item.planet] || item.planet}</span>
                        {label} · {(item.distance_from_sun!=null)? `${Number(item.distance_from_sun).toFixed(2)}°` : '-'}
                      </span>
                    );
                  })
              )}
            </div>
          </section>

          {/* B) Chart - square mock with Hour-of-Day mini ring */}
          <section className="order-5 md:[grid-column:2] md:[grid-row:2]">
            <ChartMock
              hours={hours}
              data={data}
              includeModern={includeModern}
              onToggleModern={()=> setIncludeModern(v=>!v)}
              onRefresh={refreshDashboard}
              onLocationChange={handleChartLocationChange}
              onSnap={doSnap}
              snapDisabled={manualPending}
              mode={mode}
              manualIso={activeManualIso}
              onForensic={handleOpenForensic}
              showForensicButton={false}
              onCasePrompt={handleCopyForensicCasePrompt}
              houseSystem={houseSystem}
              onHouseSystemChange={async (code) => { await (async () => handleHouseSystemChange(code))(); }}
            />
          </section>

          {/* C) Moon Condition - rectangle */}
          <section className="order-6 md:[grid-column:2] md:[grid-row:3]">
            <MoonCondition data={data} />
          </section>
          {/* Saved Snaps - below Moon Condition */}
          <section className="order-7 md:[grid-column:2] md:[grid-row:4]">
            <SavedSnapsTile
              snaps={snaps}
              loading={loadingSnaps}
              loaded={snapsLoaded}
              onRefresh={refreshSnaps}
              onLoad={loadSnap}
              onDelete={deleteSnap}
            />
          </section>
          {/* Influence & Afflictions - under Saved Snaps */}
          <section className="order-8 md:[grid-column:2] md:[grid-row:5]">
            <MetricsTile metrics={data?.metrics} specialDegrees={data?.special_degrees} />
          </section>
        </div>

        {/* Right column (col 3) */}
        <div className="order-7 md:[grid-column:3] md:[grid-row:1] space-y-4 lg:space-y-6 md:-ml-2">
          {/* D) Current Aspect - square */}
          <section className="md:[grid-column:3] md:[grid-row:1]">
            <CurrentAspectCard data={data} onOpenAnalysis={()=> setShowAspectAnalysis(true)} useMorin={useMorin} setUseMorin={setUseMorin} />
          </section>
          {/* Modal mount (fixed overlay) */}
          <AspectAnalysisModal
            open={!!showAspectAnalysis}
            onClose={()=> setShowAspectAnalysis(false)}
            specialDegrees={specialDegrees}
            useMorin={useMorin}
            includeModern={includeModern}
            dashboardData={data}
          />
          {/* E) Positions + Dignity - row 2 */}
          <section className="md:[grid-column:3] md:[grid-row:2/3] overflow-auto">
            <PositionsDignityCard data={data} />
          </section>
          {/* Current Cusps - moved up to row 3 */}
          <section className={`md:[grid-column:3] md:[grid-row:3] ${panelCls}`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Current Cusps</h3>
            </div>
            <div className="text-sm overflow-auto max-h-72 pr-1">
              <div className="grid grid-cols-4 text-xs text-zinc-500 pb-1 border-b border-zinc-200">
                <div>House</div><div>Degree</div><div>Sign</div><div>Ruler</div>
              </div>
          {(data?.house_cusps||[]).slice(0,12).map((lon, i)=> (
            <div key={i} className="grid grid-cols-4 py-1 text-sm border-b border-zinc-100 last:border-0">
              <div>H{i+1}</div>
              <div>{degreeTextFromLon(lon)}</div>
              <div>{signFromLon(lon)}</div>
              <div>{data?.house_rulers?.[String(i+1)] || '-'}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Cusp Aspects - tight 1° aspects of cusps to planets */}
      <section className={`md:[grid-column:3] md:[grid-row:4] ${panelCls}`}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-sm">Cusp Aspects</h3>
        </div>
        {/* Filter bar */}
        <div className="mb-2 flex items-center gap-2 flex-wrap">
          {/* Aspect type chips (order: All, Conj only, Hard) */}
          <div className="flex items-center gap-1">
            {['all','conj','hard'].map(mode => (
              <button key={mode} type="button" className={`px-2 py-0.5 rounded-full border text-[11px] ${cuspAspectMode===mode? 'bg-zinc-800 text-white border-zinc-800' : ''}`} onClick={()=> setCuspAspectMode(mode)}>
                {mode==='hard'? 'Hard' : mode==='all'? 'All' : 'Conj only'}
              </button>
            ))}
          </div>
          {/* Cusps dropdown */}
          <div className="relative">
            <button type="button" className="px-2 py-0.5 rounded-full border text-[11px]" onClick={()=> setShowCuspMenu(v=>!v)}>
              Cusps ({cuspSelected.size})
            </button>
            {showCuspMenu && (
              <div className="absolute z-10 mt-1 w-56 rounded-lg border bg-white shadow p-2 text-[12px]">
                <div className="mb-1 font-medium text-[12px]">Angular</div>
                <div className="flex items-center gap-2 mb-1">
                  {[...ANGULAR_SET].map(k=> (
                    <label key={k} className="flex items-center gap-1">
                      <input type="checkbox" checked={cuspSelected.has(k)} onChange={()=> toggleCusp(k)} /> {k}
                    </label>
                  ))}
                </div>
                <div className="mb-1 font-medium text-[12px]">Succedent</div>
                <div className="flex items-center gap-2 mb-1">
                  {[...SUCCEDENT_SET].map(k=> (
                    <label key={k} className="flex items-center gap-1">
                      <input type="checkbox" checked={cuspSelected.has(k)} onChange={()=> toggleCusp(k)} /> {k}
                    </label>
                  ))}
                </div>
                <div className="mb-1 font-medium text-[12px]">Cadent</div>
                <div className="flex items-center gap-2 mb-2">
                  {[...CADENT_SET].map(k=> (
                    <label key={k} className="flex items-center gap-1">
                      <input type="checkbox" checked={cuspSelected.has(k)} onChange={()=> toggleCusp(k)} /> {k}
                    </label>
                  ))}
                </div>
                <div className="flex items-center justify-between">
                  <button type="button" className="px-2 py-0.5 rounded border" onClick={setAllCusps}>All</button>
                  <button type="button" className="px-2 py-0.5 rounded border" onClick={clearCusps}>None</button>
                  <button type="button" className="px-2 py-0.5 rounded border" onClick={()=> setShowCuspMenu(false)}>Close</button>
                </div>
              </div>
            )}
          </div>
          {/* Phase chips */}
          <div className="flex items-center gap-1">
            {['any','applying','separating'].map(ph => (
              <button key={ph} type="button" className={`px-2 py-0.5 rounded-full border text-[11px] ${cuspPhase===ph? 'bg-zinc-800 text-white border-zinc-800' : ''}`} onClick={()=> setCuspPhase(ph)}>
                {ph.charAt(0).toUpperCase()+ph.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex-1" />
        </div>
        <div className="astro-scroll-shell max-h-72" onClick={()=> setShowCuspMenu(false)}>
          <div className="astro-scroll space-y-3 max-h-72">
            {(() => {
              const src = data?.cusp_aspects || {};
              const hasData = !!data;
              const rawHitCount = Object.values(src).reduce((count, value) => {
                return count + (Array.isArray(value) ? value.length : 0);
              }, 0);
              if (!hasData) {
                return <div className="text-sm text-zinc-500">Loading cusp aspects...</div>;
              }
              const allKeys = Array.from({length:12}, (_,i)=>`H${i+1}`);
              // Keep an empty selection empty so the "None" action behaves as a
              // real filter state instead of silently reverting to all cusps.
              const keys = allKeys.filter(k => cuspSelected.has(k));
              const rows = [];
            for (const k of keys) {
              const items = Array.isArray(src[k]) ? src[k] : [];
              let list = items.filter(it => {
                if (cuspAspectMode === 'hard' && it?.category !== 'hard') return false;
                if (cuspAspectMode === 'conj' && String(it?.aspect).toLowerCase() !== 'conjunction') return false;
                const ph = String(it?.phase || '').toLowerCase();
                if (cuspPhase !== 'any' && ph !== cuspPhase) return false;
                if (it?.orb == null) return false;
                if (Number(it.orb) > 1.0 + 1e-6) return false;
                return true;
              });
              // Keep backend ordering (by orb, hard first). No user sort.
              if (list.length === 0) continue;
              rows.push(
                <div key={k}>
                  <div className="font-medium text-[12px] mb-1">{k}</div>
                  <ul className="space-y-2">
                    {list.slice(0, 16).map((it, idx) => {
                      const orb = (it?.orb != null) ? `${Number(it.orb).toFixed(2)}°` : '-';
                      const phase = it?.phase || '';
                      const band = it?.band || (Number(it?.orb||10) <= 0.5 ? 'partile' : 'tight');
                      const dex = (typeof it?.dexter === 'boolean') ? (it.dexter ? 'dexter' : 'sinister') : '';
                      const origin = (it?.origin_house != null) ? `H${it.origin_house}` : '';
                      const originTitle = it?.origin_domain ? String(it.origin_domain) : '';
                      const label = `${it.planet}${origin? ' ('+origin+')':''} ${it.aspect}`;
                      return (
                        <li
                          key={`${k}-${idx}`}
                          className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-2.5"
                          title={originTitle}
                        >
                          <div className="flex items-start gap-2">
                            <span className="inline-flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full border border-zinc-200 bg-white px-1.5 text-[12px] leading-none">
                              {PlanetSymbols[it.planet] || it.planet}
                            </span>
                            <div className="min-w-0 flex-1">
                              <div className="break-words text-[12px] font-medium leading-5 text-zinc-800">
                                {label}
                              </div>
                              {originTitle && (
                                <div className="mt-1 break-words text-[11px] leading-4 text-zinc-600">
                                  {originTitle}
                                </div>
                              )}
                              <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-zinc-500">
                                <span className="tabular-nums">{orb}</span>
                                {phase && <span>{phase}</span>}
                                {dex && <span className="rounded border border-zinc-200 bg-white px-1.5 py-0.5 text-zinc-700">{dex}</span>}
                                {band && <span className="rounded border border-zinc-200 bg-white px-1.5 py-0.5 text-zinc-700">{band}</span>}
                              </div>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            }
              if (rows.length) return rows;
              if (rawHitCount > 0) {
                return <div className="text-zinc-500">No cusp aspects match the current filters.</div>;
              }
              return <div className="text-zinc-500">No cusp-to-planet aspects within 1° for this chart.</div>;
            })()}
          </div>
        </div>
      </section>

      {/* Compass Bearings (planets only) */}
      <section className={`md:[grid-column:3] md:[grid-row:5]`}>
        <CompassTile
          includeModern={includeModern}
          timestamp={data?.timestamp}
          mode={mode}
          location={data?.location}
          planets={data?.planets}
          houseCusps={data?.house_cusps}
        />
      </section>
      <section className={`md:[grid-column:3] md:[grid-row:6]`}>
        <AsteroidsTile asteroids={data?.asteroids} />
      </section>
        </div>
      </div>

      {/* old bottom-row tiles removed per new layout spec */}
      {openingForensic && !showForensic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div
            className={`w-full max-w-[340px] rounded-2xl border p-4 shadow-xl ${
              darkMode
                ? 'border-zinc-700 bg-zinc-900 text-zinc-100'
                : 'border-zinc-200 bg-white text-zinc-900'
            }`}
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className={`text-[11px] font-medium uppercase tracking-[0.16em] ${darkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    Forensic Workspace
                  </div>
                  <div className="mt-1 text-sm font-semibold leading-5">Opening Forensic...</div>
                </div>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                    darkMode
                      ? 'border-zinc-700 bg-zinc-800 text-zinc-300'
                      : 'border-zinc-200 bg-zinc-50 text-zinc-600'
                  }`}
                >
                  Preparing
                </span>
              </div>
              <p className={`text-[12px] leading-5 ${darkMode ? 'text-zinc-300' : 'text-zinc-600'}`}>
                Preparing the forensic workspace before it opens.
              </p>
              <div className={`h-1.5 overflow-hidden rounded-full ${darkMode ? 'bg-zinc-800' : 'bg-zinc-100'}`}>
                <div className={`h-full w-2/3 rounded-full animate-pulse ${darkMode ? 'bg-sky-400' : 'bg-sky-500'}`} />
              </div>
            </div>
          </div>
        </div>
      )}
      {showForensic && (
        <ForensicDashboard
          onClose={handleCloseForensic}
          clockContext={buildClockContext()}
        />
      )}
      {!isProd && showResearch && (
        <ResearchMode onClose={()=> setShowResearch(false)} />
      )}
        {showTraits && (
          <TraitProfileModal
            onClose={handleCloseTraitProfile}
            specialDegrees={specialDegrees}
            mode={mode}
            manualIso={activeManualIso}
            manualLocation={data?.location || manualLocation}
            timezone={data?.timezone || null}
            houseSystem={houseSystem}
            chartSnapshot={data}
            fixedStarHits={Array.isArray(data?.fixed_star_hits) ? data.fixed_star_hits : []}
          />
        )}
      {showSynastry && (
        <SynastryModal
          open={showSynastry}
          onClose={handleCloseSynastry}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
        />
      )}
      {showTransits && (
        <TransitsModal
          open={showTransits}
          onClose={handleCloseTransits}
          onJumpToTime={jumpToIso}
          defaultHouseSystem={houseSystem}
          initialNatalContext={activeTransitSeed}
        />
      )}
      {showElection && (
        <ElectionModal
          open={showElection}
          onClose={handleCloseElection}
          onJumpToTime={jumpToIso}
          defaultHouseSystem={houseSystem}
        />
      )}
      {showAstrocartography && (
        <AstrocartographyModal
          open={showAstrocartography}
          onClose={handleCloseAstrocartography}
          defaultHouseSystem={houseSystem}
          initialTransitContext={activeTransitSeed}
          snaps={snaps}
          activeSnapId={activeSnapId || inferredActiveSnapId || ''}
          onCreateSnap={doSnap}
        />
      )}
      {showNamePrompt && (
        <NamePromptModal
          open={showNamePrompt}
          type={namePromptType}
          onCancel={()=> setShowNamePrompt(false)}
          onSubmit={handleNamePromptSubmit}
        />
      )}
    </div>
  );
};

export default AstroClock;

function ForensicDashboard({ onClose, clockContext }){
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [features, setFeatures] = useState(null);
  const [viability, setViability] = useState({ asc_desc: null, correlation: null, angular: null, logic: null });
  const [caseType, setCaseType] = useState('general'); // general|child|adult_female
  const [abductionMode, setAbductionMode] = useState(false);
  const [includeRaw, setIncludeRaw] = useState(false);
  const [copiedBrief, setCopiedBrief] = useState(false);
  const [originLat, setOriginLat] = useState('');
  const [originLon, setOriginLon] = useState('');
  const [fetchingAbd, setFetchingAbd] = useState(false);
  const [abdMsg, setAbdMsg] = useState('');
  const [mapHover, setMapHover] = useState(null); // { lat, lon }
  const [placeName, setPlaceName] = useState('');
  const [placeLoading, setPlaceLoading] = useState(false);
  const [showBackAz, setShowBackAz] = useState(false);
  const [flipSubHorizon, setFlipSubHorizon] = useState(false);
  const [expandedFindingIndex, setExpandedFindingIndex] = useState(null);
  const forensicClockContext = useMemo(() => ({ ...(clockContext || {}) }), [JSON.stringify(clockContext || {})]);
  const rawFindings = useMemo(() => (
    Array.isArray(data?.findings) ? data.findings.filter((finding) => finding && typeof finding === 'object') : []
  ), [data?.findings]);
  const replayAxes = useMemo(() => deriveForensicReplayAxes(data || {}), [data]);
  const categoryEntries = useMemo(() => (
    data?.categories && typeof data.categories === 'object'
      ? Object.entries(data.categories).sort((a, b) => String(a[0]).localeCompare(String(b[0])))
      : []
  ), [data?.categories]);

  useEffect(() => {
    setExpandedFindingIndex(null);
  }, [data?.timestamp, rawFindings.length]);

  const fetchForensic = useCallback(async (optsExtra={}) => {
    try {
      const opts = { ...forensicClockContext, caseType };
      if (optsExtra && optsExtra.abduction) {
        opts.abduction = true;
        if (optsExtra.origin) opts.origin = optsExtra.origin;
        if (optsExtra.line_zones != null) opts.line_zones = !!optsExtra.line_zones;
        if (optsExtra.corridor_deg != null) opts.corridor_deg = optsExtra.corridor_deg;
      }
      const res = await AstroClockAPI.getForensic(opts);
      if (res?.success) {
        setData(res);
        setFeatures(res.features || null);
        setAbdMsg(optsExtra && optsExtra.abduction ? 'Abduction map fetched.' : '');
      }
    } catch(err){
      console.error('Abduction fetch failed:', err);
      try { setAbdMsg(`Abduction fetch failed: ${String(err?.message||err)} (API ${window.API_BASE_URL||'unknown'})`); } catch(_){ setAbdMsg('Abduction fetch failed.'); }
      throw err;
    }
  }, [forensicClockContext, caseType]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        await fetchForensic();
      } catch {}
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [fetchForensic]);

  function buildAIBrief(includeRawValues){
    try {
      const lines = [];
      const dash = data || {};
      const f = features || {};
      // Victim basics
      const cusps = f.house_cusps || [];
      const ascSignName = (()=>{ try { const L = Number(cusps[0]); const signs=['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']; return isFinite(L)? signs[Math.floor(((L%360)+360)%360/30)] : null; } catch{ return null; } })();
      const rulers = f.house_rulers || {};
      const primaryRuler = f.houses?.first_ruler || rulers['1'] || rulers[1] || null;
      const coRulers = ['Moon', ...(caseType==='child'? ['Mercury']: []), ...(caseType==='adult_female'? ['Venus']: [])].filter((v,i,arr)=> arr.indexOf(v)===i);
      const moon = f.planets?.['Moon'] || {};
      const mt = dash.moon_timeline || {};
      const voc = (typeof mt.in_voc === 'boolean') ? mt.in_voc : Boolean((dash.moon || f.moon || {}).void_of_course);
      const moonPos = `${moon.sign||'-'} ${isFinite(moon.longitude)? degreeTextFromLon(moon.longitude):'-'} (H${moon.house??'-'})`;

      // Perpetrator basics
      const seventhRuler = f.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
      const pl = f.planets || {};
      const prInfo = pl[seventhRuler] || {};
      const degFlags = [];
      if (prInfo.anaretic) degFlags.push('Anaretic');
      if (prInfo.ingress) degFlags.push('Ingress');
      if (prInfo.middegree) degFlags.push('Mid-degree');
      if (prInfo.via_combusta) degFlags.push('Via combusta');
      const fsSunMoon = Array.isArray(f.fixed_stars_list)? f.fixed_stars_list.filter(h=> h?.target_type==='planet' && (h?.target==='Sun' || h?.target==='Moon')): [];
      const fsCusps = Array.isArray(f.fixed_stars_list)? f.fixed_stars_list.filter(h=> h?.target_type==='cusp'): [];

      // Witnesses
      const houseList = (h)=> Object.entries(pl).filter(([,p])=> p?.house===h).map(([n])=> n);
      const witnesses = ['Mercury', ...houseList(3)];
      const associates = houseList(11);
      const hidden = [...houseList(6), ...houseList(12)];

      // Deception config (reuse simplified flags)
      const asp = f.aspects || {};
      const getA = (a,b)=> Boolean(asp[`${a}_to_${b}`] || asp[`${b}_to_${a}`]);
      const houses = f.houses || {};
      const deceFlags = [];
      if (getA('Mercury','Neptune')) deceFlags.push('Mercury–Neptune');
      if (pl?.Mercury?.retrograde) deceFlags.push('Mercury retrograde');
      if ((dash.features?.solar || f.solar || {}).combustion?.includes?.('Mercury')) deceFlags.push('Mercury combust');
      if (pl?.Mercury?.house===12) deceFlags.push('Mercury in 12th');
      if (pl?.Mercury?.mute_sign) deceFlags.push('Mercury in mute sign');
      ['Sun','Moon','Mercury','Venus','Mars'].forEach(pn=> { if (getA('Neptune', pn)) deceFlags.push('Neptune->personal'); });
      if (pl?.Sun?.house===12 || pl?.Moon?.house===12) deceFlags.push('Sun/Moon in 12th');
      if (houses?.emphasis12_strong) deceFlags.push('12th emphasis');
      if (houses?.seventh_ruler_in_12th) deceFlags.push('7th ruler in 12th');
      if (getA('Mars','Neptune')) deceFlags.push('Mars–Neptune');
      if (getA('Venus','Saturn')) deceFlags.push('Venus–Saturn');
      if (houses?.mute_signs_on_angles) deceFlags.push('Mute signs on angles');
      if (houses?.mute_sign_on_3rd_or_9th) deceFlags.push('Mute signs on 3rd/9th');
      if (houses?.north_node_house===8) deceFlags.push('NN in 8th');
      if (houses?.north_node_house===4) deceFlags.push('NN in 4th');

      // Final Outcome
      const cusp4 = Number((f.house_cusps||[])[3]);
      const icSign = isFinite(cusp4)? signFromLon(cusp4): null;
      const icExpl = icSign ? (dash.ic_sign_meanings?.[icSign]?.outcome) : null;
      const r4 = rulers['4'] || rulers[4] || null;
      const r4h = r4 ? pl?.[r4]?.house : null;
      const r4Expl = (r4h!=null)? (dash.ic_ruler_house_meanings?.[String(r4h)]?.outcome) : null;
      const in4 = Object.entries(pl).filter(([,p])=> p?.house===4).map(([n])=> n);
      const in4Expl = in4.map(nm => {
        const e = dash.ic_planet_in_4th?.[nm];
        return e? `${nm} - ${e}` : nm;
      });
      const nodesIn4 = in4.filter(nm => nm==='North Node' || nm==='South Node' || nm==='Node');

      // Abduction / Location & Distance Cues
      let abdBlock = '';
      if (abductionMode) {
        abdBlock = buildAbductionCueReportLines({ data, features: f }).join('\n');
      }

      // Light mediation
      const lm = dash.light_mediation || {};

      const header = `You are a forensic astrologer/investigator. Using the chart-derived data below, produce a concise, auditable report with these sections: Victim Analysis, Perpetrator Analysis, Witness & Accomplice Detection, Deception Configuration, Final outcome determination${abductionMode? ', Abduction cues':''}.`;
      lines.push(header, '');
      lines.push('Victim Analysis');
      lines.push(`ASC Sign: ${ascSignName||'-'}`);
      lines.push(`Primary Ruler: ${primaryRuler||'-'}; Co-rulers: ${coRulers.join(', ')||'-'}`);
      lines.push(`Moon: ${moonPos}; VoC ${voc? 'Yes':'No'}`);
      lines.push('');
      lines.push('Perpetrator Signals');
      lines.push(`7th-house ruler: ${seventhRuler||'-'} · Degree markers: ${degFlags.join(', ')||'-'}`);
      lines.push(`Light mediation: ${lm.translation? `Translation${lm.translator? ' via '+lm.translator:''}` : (lm.collection? `Collection${lm.collector? ' by '+lm.collector:''}` : '-')}`);
      if (fsSunMoon.length) lines.push(`Sun/Moon fixed stars: ${fsSunMoon.map(x=> `${x.name}↔${x.target}`).join('; ')}`);
      if (fsCusps.length) lines.push(`Cusp fixed stars: ${fsCusps.map(x=> `${x.name}↔${x.target}`).join('; ')}`);
      // Dominant Signature (top 1–2)
      try {
        const dom = dash.dominance?.planets || {};
        const domArr = Object.entries(dom).map(([name,v])=> ({ name, score: Number(v?.score)||0, level: String(v?.level||'') })).sort((a,b)=> b.score-a.score);
        if (domArr.length){
          const top2 = domArr.slice(0,2).map(d=> `${d.name} ${d.score} (${d.level})`).join(', ');
          lines.push(`Dominant signals: ${top2}`);
          // Behavioral profile + image prompt suggestion
          const profiles = dash.perpetrator_profiles?.behavioral_trait_matrix || dash.perpetrator_profiles || {};
          let chosen = null;
          for (const d of domArr){ const key = `${d.name}_dominated`; const entry = profiles?.[key] || profiles?.[d.name] || null; if (entry){ chosen = { planet: d.name, entry }; break; } }
          if (chosen && chosen.entry){
            const bc = chosen.entry.behavioral_characteristics || {};
            const hints = [];
            ['motive','method','temperament','public_behavior','profession'].forEach(k=> { if (bc[k]) hints.push(String(bc[k])); });
            if (bc.physical) hints.unshift(String(bc.physical));
            if (hints.length) lines.push(`Behavioral read: ${chosen.planet} - ${hints.slice(0,2).join(' · ')}`);
            const phys = bc.physical || '';
            const temp = bc.temperament || '';
            const meth = bc.method || '';
            const imgPrompt = `forensic composite portrait of a ${chosen.planet}-dominated perpetrator, ${phys} ${temp? '- '+temp:''}${meth? ' - '+meth:''}, realistic, neutral lighting, investigative sketch style`;
            lines.push(`Visualize (profiling image): Provide a short verbal composite and an image prompt. Example prompt: ${imgPrompt}`);
          }
        }
      } catch(_){ /* ignore dominant errors */ }
      // Relationship Link Determination (Algorithm)
      try {
        const firstRuler = f.houses?.first_ruler || rulers['1'] || rulers[1] || null;
        const seventhRuler = f.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
        const sr = { Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter' };
        const exaltation = { Sun:'Aries', Moon:'Taurus', Mercury:'Virgo', Venus:'Pisces', Mars:'Capricorn', Jupiter:'Cancer', Saturn:'Libra' };
        const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
        const opp = (s) => signs[(signs.indexOf(s)+6)%12] || null;
        const triOf = (sign) => {
          if (!sign) return null;
          if (['Aries','Leo','Sagittarius'].includes(sign)) return 'Fire';
          if (['Taurus','Virgo','Capricorn'].includes(sign)) return 'Earth';
          if (['Gemini','Libra','Aquarius'].includes(sign)) return 'Air';
          if (['Cancer','Scorpio','Pisces'].includes(sign)) return 'Water';
          return null;
        };
        const planets = f.planets || {};
        const victimSign = planets?.[firstRuler]?.sign; const perpSign = planets?.[seventhRuler]?.sign;
        const victimHouse = planets?.[firstRuler]?.house; const perpHouse = planets?.[seventhRuler]?.house;
        const recData = dash?.receptions || {};
        const mutual = Array.isArray(recData.mutual)? recData.mutual : [];
        const uni = Array.isArray(recData.top_unilateral)? recData.top_unilateral : [];
        const starRel = dash?.relationship_star_hits || {};

        // Level 1
        const directVictRulesPerp = victimSign && sr[perpSign] === firstRuler;
        const directPerpRulesVict = perpSign && sr[victimSign] === seventhRuler;
        // Level 2
        const isMutual = mutual.some(m => (m.p1===firstRuler && m.p2===seventhRuler) || (m.p1===seventhRuler && m.p2===firstRuler));
        // Level 3
        const level3 = victimSign && perpSign && (triOf(victimSign) === triOf(perpSign));
        // Level 4
        const perpExaltSign = exaltation[seventhRuler];
        const victExaltSign = exaltation[firstRuler];
        const level4_victim_in_exalt_of_perp = victimSign && (victimSign === perpExaltSign);
        const level4_victim_in_fall_of_perp = victimSign && (victimSign === opp(perpExaltSign));
        const level4_perp_in_exalt_of_victim = perpSign && (perpSign === victExaltSign);
        const level4_perp_in_fall_of_victim = perpSign && (perpSign === opp(victExaltSign));
        // Level 5
        const level5_terms = uni.some(u => ((u.receiving===firstRuler && u.received===seventhRuler) || (u.receiving===seventhRuler && u.received===firstRuler)) && (u.dignities||[]).includes('term'));

        // House analysis
        const houseFlags = [];
        if (victimHouse===1) houseFlags.push('Victim ruler in 1st');
        if (victimHouse===7) houseFlags.push('Victim ruler in 7th');
        if (victimHouse===4||victimHouse===10) houseFlags.push('Victim ruler in 4th/10th');
        if (victimHouse===8) houseFlags.push('Victim ruler in 8th');
        if (victimHouse===12) houseFlags.push('Victim ruler in 12th');
        if (perpHouse===1) houseFlags.push('Perp ruler in 1st');
        if (perpHouse===4||perpHouse===10) houseFlags.push('Perp ruler in 4th/10th');
        if (perpHouse===6) houseFlags.push('Perp ruler in 6th');
        if (perpHouse===11) houseFlags.push('Perp ruler in 11th');
        const sameHouse = (victimHouse!=null && perpHouse!=null && victimHouse===perpHouse);
        const crit = [];
        // Only flag family involvement in crit when BOTH rulers are in 4th OR BOTH are in 10th
        const _vh = Number(victimHouse), _ph = Number(perpHouse);
        const critSameFamily = (_vh === 4 && _ph === 4) || (_vh === 10 && _ph === 10);
        if (critSameFamily) crit.push('Both rulers in same family house (4 or 10)');
        // Consolidate 1st/7th exchange into a single label (avoid duplicate)
        if ((victimHouse===1 && perpHouse===7) || (victimHouse===7 && perpHouse===1)) crit.push('1st/7th exchange');
        if (sameHouse) crit.push('Both rulers in same house');

        // Traditional cues
        const h7Planets = Object.entries(planets).filter(([,p])=> p?.house===7).map(([n])=> n);
        const trad = [];
        if (h7Planets.includes('Venus')) trad.push('Venus in 7th');
        if (h7Planets.includes('Mars')) trad.push('Mars in 7th');
        if ((planets?.Sun?.house===4)) trad.push('Sun in 4th');
        if ((planets?.Moon?.house===10)) trad.push('Moon in 10th');
        if (Object.values(planets).some(p=> p?.house===5)) trad.push('5th house connection');
        if (Object.values(planets).some(p=> p?.house===3)) trad.push('3rd house emphasis');

        // Aspects
        const aspMap = f.aspects || {};
        const a = aspMap[`${firstRuler}_to_${seventhRuler}`] || aspMap[`${seventhRuler}_to_${firstRuler}`] || null;
        const aspType = a?.type || null;
        const aspectFlags = [];
        if (aspType) {
          const easy=['conjunction','trine','sextile']; const hard=['square','opposition'];
          if (easy.includes(aspType)) aspectFlags.push(`Harmonious (${aspType})`);
          if (hard.includes(aspType)) aspectFlags.push(`Stressful (${aspType})`);
        } else { aspectFlags.push('No direct aspect'); }

        // Degrees and fixed stars on significators
        const degInt = (nm)=> { const d = planets?.[nm]?.degree_in_sign; return (typeof d==='number')? Math.round(d): null; };
        const dVict = degInt(firstRuler); const dPerp = degInt(seventhRuler);
        const degFlags2 = [];
        if (dVict===0) degFlags2.push('0° (victim)'); if (dPerp===0) degFlags2.push('0° (perp)');
        if (dVict===15) degFlags2.push('15° (victim)'); if (dPerp===15) degFlags2.push('15° (perp)');
        if (dVict===29) degFlags2.push('29° (victim)'); if (dPerp===29) degFlags2.push('29° (perp)');
        const ascStars = (starRel?.asc_ruler||[]).map(h=> h?.name).filter(Boolean);
        const dscStars = (starRel?.dsc_ruler||[]).map(h=> h?.name).filter(Boolean);

        // Scoring
        let score = 0; const reasons = [];
        // House crossovers scoring
        if (victimHouse===7) { score+=2; reasons.push('Victim ruler in 7th (+2)'); }
        if (perpHouse===1) { score+=2; reasons.push('Perp ruler in 1st (+2)'); }
        if (perpHouse===7) { score+=1; reasons.push('Perp ruler in 7th (+1)'); }
        if (sameHouse) { score+=2; reasons.push('Both rulers in same house (+2)'); }
        { const angSet = new Set([1,4,7,10]); if (angSet.has(Number(victimHouse)) && angSet.has(Number(perpHouse))) { score+=1; reasons.push('Both rulers angular (+1)'); } }
        if (directVictRulesPerp) { score+=3; reasons.push('Victim ruler rules perpetrator sign'); }
        if (directPerpRulesVict) { score+=3; reasons.push('Perp ruler rules victim sign'); }
        if (isMutual) { score+=4; reasons.push('Mutual reception'); }
        if (level3) { score+=2; reasons.push('Shared triplicity'); }
        if (level4_victim_in_exalt_of_perp) { score+=2; reasons.push('Victim in exaltation of perpetrator'); }
        if (level4_perp_in_exalt_of_victim) { score+=2; reasons.push('Perp in exaltation of victim'); }
        if (level4_victim_in_fall_of_perp) { score+=1; reasons.push('Victim in fall of perpetrator'); }
        if (level4_perp_in_fall_of_victim) { score+=1; reasons.push('Perp in fall of victim'); }
        if (uni.some(u=> (u.receiving===firstRuler && u.received===seventhRuler) || (u.receiving===seventhRuler && u.received===firstRuler))) { score+=1; reasons.push('Directional reception'); }
        // Add a modest score only when BOTH rulers are in 4th or BOTH in 10th
        if (critSameFamily) { score+=1; reasons.push('Family same-house (4 or 10)'); }
        // Translation/Collection of light strengthens linkage
        if (lm?.translation) { score+=1; reasons.push('Translation of light'); }
        else if (lm?.collection) { score+=1; reasons.push('Collection of light'); }
        if (h7Planets.includes('Venus') || h7Planets.includes('Mars')) { score+=1; reasons.push('7th-house indicator'); }
        if (aspType){
          const easy=['conjunction','trine','sextile']; const hard=['square','opposition'];
          if (easy.includes(aspType)) { score+=2; reasons.push('Harmonious aspect'); }
          else if (hard.includes(aspType)) { score+=1; reasons.push('Stressful aspect'); }
          if (a?.applying === true) { score+=1; reasons.push('Applying aspect'); }
        }
        if (dVict===0||dVict===15||dVict===29||dPerp===0||dPerp===15||dPerp===29) { score+=1; reasons.push('Critical degree'); }
        const violentStars = new Set(['Algol','Antares']); const protectStars = new Set(['Spica']);
        const hasViolent = [...ascStars, ...dscStars].some(n=> violentStars.has(n));
        const hasProtect = [...ascStars, ...dscStars].some(n=> protectStars.has(n));
        if (hasViolent) { score+=2; reasons.push('Violent fixed star'); }
        if (hasProtect) { score+=1; reasons.push('Protective fixed star'); }
        const relationshipSummary = summarizeForensicRelationshipLink({
          score,
          victimHouse,
          perpHouse,
          seventhHousePlanets: h7Planets,
          isMutual,
          forensicResult: dash,
        });

        lines.push('', 'Relationship Signals');
        const bothIn4 = Number(victimHouse) === 4 && Number(perpHouse) === 4;
        const bothIn10 = Number(victimHouse) === 10 && Number(perpHouse) === 10;
        const relationshipRows = buildRelationshipDisplayRows({
          firstRuler,
          moonContacts: aspectTo('Moon'),
          ascRulerContacts: aspectTo(firstRuler),
          directVictRulesPerp,
          directPerpRulesVict,
          isMutual,
          level3,
          exaltationFallFlags: [
            level4_victim_in_exalt_of_perp?'victim in exaltation of perpetrator':null,
            level4_perp_in_exalt_of_victim?'perpetrator in exaltation of victim':null,
            level4_victim_in_fall_of_perp?'victim in fall of perpetrator':null,
            level4_perp_in_fall_of_victim?'perpetrator in fall of victim':null,
          ].filter(Boolean),
          level5Terms: level5_terms,
          houseConnections: (bothIn4 || bothIn10)
            ? ['shared family-house placement (4th/10th)']
            : houseFlags.concat(crit),
          traditionalCues: trad,
          aspectTies: aspectFlags,
          degreeStarCues: degFlags2.concat([
            ascStars.length? `ASC ruler on ${ascStars.join('/')}`: null,
            dscStars.length? `DSC ruler on ${dscStars.join('/')}`: null,
          ].filter(Boolean)),
          score,
          relationshipType: relationshipSummary.relationshipType,
          confidence: relationshipSummary.confidence,
        });
        lines.push(`Contact signals: ${relationshipRows.contactSignals}`);
        lines.push(`Rulership links: ${relationshipRows.rulershipLinks}`);
        lines.push(`Mutual reception: ${relationshipRows.mutualReception}`);
        lines.push(`Shared triplicity: ${relationshipRows.sharedTriplicity}`);
        lines.push(`Exaltation/fall ties: ${relationshipRows.exaltationFallTies}`);
        lines.push(`Term/bounds ties: ${relationshipRows.termBoundsTies}`);
        lines.push(`House overlap: ${relationshipRows.houseOverlap}`);
        lines.push(`Traditional cues: ${relationshipRows.traditionalCues}`);
        lines.push(`Aspect ties: ${relationshipRows.aspectTies}`);
        lines.push(`Degree/star cues: ${relationshipRows.degreeStarCues}`);
        lines.push(`Connection summary: ${relationshipRows.connectionSummary}`);
      } catch(_) {}
      lines.push('');
      lines.push('Witness & Accomplice Detection');
      lines.push(`Mercury (witness/sibling): H${pl?.Mercury?.house ?? '-'}`);
      lines.push(`H3 (neighbors/local): ${houseList(3).join(', ')||'-'}; H11 (associates): ${associates.join(', ')||'-'}; H6/12 (hidden): ${hidden.join(', ')||'-'}`);
      lines.push('');
      lines.push('Deception Configuration');
      lines.push(`Indicators: ${deceFlags.join('; ')||'-'}`);
      lines.push('');
      lines.push('Final outcome determination');
      lines.push(`IC sign: ${icSign||'-'}${icExpl? ' - '+icExpl:''}`);
      lines.push(`4th ruler: ${r4? `${r4} in H${r4h??'-'}`:'-'}${r4Expl? ' - '+r4Expl:''}`);
      lines.push(`Planets in 4th: ${in4Expl.join('; ')||'-'}${nodesIn4.length? ' · Node modifier present':''}`);
      lines.push('Final outcome verbal composite: Provide a concise narrative of how the matter ends (who/what determines closure, tone of the ending, and likely setting), integrating IC sign, 4th‑ruler placement, and 4th‑house occupants.');
      if (abductionMode){ lines.push(''); lines.push(abdBlock); }

      if (includeRawValues) {
        // Append a compact RAW block to aid AI with precise values
        const raw = {};
        try {
          raw.asc_cusp = (f.house_cusps||[])[0];
          raw.house_cusps = (f.house_cusps||[]).slice(0,12);
          raw.house_rulers = f.house_rulers || {};
          raw.planets = Object.fromEntries(Object.entries(f.planets||{}).map(([k,p])=> [k, {
            sign: p.sign, house: p.house, longitude: p.longitude, dignity_score: p.dignity_score,
            retrograde: p.retrograde
          }]));
          // Applying aspects with details
          raw.applying_aspects = Object.entries(f.aspects||{}).filter(([_,v])=> v && v.applying===true)
            .map(([k,v])=> ({ key:k, type:v.type, orb:v.orb, ttp:v.time_to_perfection, within_sign: v.perfection_within_sign }));
          raw.moon_timeline = dash.moon_timeline || {};
          raw.light_mediation = dash.light_mediation || {};
          if (abductionMode) {
            const rulersRaw = f.house_rulers || {};
            const fr = f.houses?.first_ruler || rulersRaw['1'] || rulersRaw[1] || null;
            const pl = f.planets || {};
            const c1 = Number((f.house_cusps||[])[0]);
            const ascSign = isFinite(c1)? signFromLon(c1): null;
            const sign = (pl?.[fr]?.sign) || ascSign;
            const house = (pl?.[fr]?.house != null)? pl[fr].house : 1;
            raw.abduction_pivot = { first_ruler: fr, sign, house, moon: { sign: pl?.Moon?.sign, house: pl?.Moon?.house } };
          }
        } catch(_){}
        lines.push('', 'RAW', JSON.stringify(raw, null, 2));
      }
      return lines.join('\n');
    } catch(e){ return ''; }
  }

  const card = (title, body) => (
    <section className={panelCls}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">{title}</h3>
      </div>
      {body}
    </section>
  );

  const ascSign = (() => {
    try {
      const cusps = features?.house_cusps || [];
      if (!Array.isArray(cusps) || cusps.length < 1) return null;
      const L = Number(cusps[0])||0; const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
      return signs[Math.floor(((L%360)+360)%360 / 30)];
    } catch { return null; }
  })();
  const signRuler = {
    Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter'
  };

  // Build a minimal HTML report with optional vector abduction map (offline-safe)
  function buildReportHTML() {
    try {
      let brief = '';
      try { brief = String(buildAIBrief(includeRaw) || ''); } catch { brief = ''; }
      const ts = new Date().toLocaleString();
      const dash = data || {};
      const f = features || {};
      // Case header fields
      const caseHeader = (() => {
        const parts = [];
        if (dash?.timestamp) parts.push(`Time: ${new Date(dash.timestamp).toLocaleString()}`);
        if (dash?.location) parts.push(`Location: ${dash.location}`);
        if (dash?.timezone_label) parts.push(`TZ: ${dash.timezone_label}`);
        return parts.join(' · ');
      })();
      const svg = (() => {
        try {
          if (!abductionMode) return '';
          const abd = data?.abduction_map || {};
          const origin = abd.origin || {};
          let lat = Number(origin.lat); let lon = Number(origin.lon);
          if (!isFinite(lat) || !isFinite(lon)) return '';
          const bearings = Array.isArray(abd.bearings)? abd.bearings : [];
          const firstRulerName = (()=> {
            try {
              const rulers = f?.house_rulers || {};
              return f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
            } catch { return null; }
          })();
          const processedBearings = buildProcessedAbductionBearings(bearings, firstRulerName);
          const size = 520; const cx = size/2; const cy = size/2; const outerKm = 40; const kmToPx = (size*0.42)/outerKm;
          const rings = [3,12,40];
          const roleStyle = (role) => {
            const style = getAbductionRoleStyle(role);
            return {
              color: style.color,
              width: style.weight,
              dash: style.dashArray ? String(style.dashArray).replace(/\s+/g, ',') : null,
            };
          };
          const toRad = (v)=> v*Math.PI/180; const norm360=(x)=> (x%360+360)%360;
          const pointAt = (azDeg, km) => {
            const r = Math.min(km, outerKm) * kmToPx;
            const a = toRad(90 - norm360(azDeg));
            const x = cx + r * Math.cos(a);
            const y = cy - r * Math.sin(a);
            return [x, y];
          };
          const lines = processedBearings.slice(0,6).map(b => {
            const az = Number(b?.azimuth_deg); if (!isFinite(az)) return null;
            const st = roleStyle(b?.role);
            const [x2,y2] = pointAt(az, outerKm);
            return `<line x1="${cx}" y1="${cy}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${st.color}" stroke-width="${st.width}" ${st.dash? `stroke-dasharray=\"${st.dash}\"`:''} stroke-linecap="round" />`;
          }).filter(Boolean).join('');
          const ringsSvg = rings.map(km => `<circle cx="${cx}" cy="${cy}" r="${(km*kmToPx).toFixed(1)}" fill="none" stroke="#e5e7eb" stroke-width="1" />`).join('');
          const originDot = `<circle cx="${cx}" cy="${cy}" r="4" fill="#111827" />`;
          const legend = `
            <g transform="translate(${size-170}, 16)" font-size="10" fill="#111827">
              <text x="0" y="0">Legend</text>
              ${getAbductionLegendEntries().map((entry, i)=>{
                const r = entry.role;
                const s=roleStyle(r); const y= (i+1)*14;
                return `<g transform=\"translate(0,${y})\"><line x1=\"0\" y1=\"-4\" x2=\"22\" y2=\"-4\" stroke=\"${s.color}\" stroke-width=\"2\" ${s.dash?`stroke-dasharray=\"${s.dash}\"`:''} /><text x=\"26\" y=\"0\">${entry.legendLabel}</text></g>`;
              }).join('')}
            </g>`;
          return `<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"${size}\" height=\"${size}\" viewBox=\"0 0 ${size} ${size}\"><rect x=\"0\" y=\"0\" width=\"${size}\" height=\"${size}\" fill=\"#ffffff\" />${ringsSvg}${originDot}${lines}${legend}</svg>`;
        } catch { return ''; }
      })();
      // Bearings table (top 6)
      const bearingsTable = (() => {
        try {
          if (!abductionMode) return '';
          const abd = data?.abduction_map || {};
          const bearings = Array.isArray(abd.bearings)? abd.bearings : [];
          const firstRulerName = (()=> {
            try {
              const rulers = f?.house_rulers || {};
              return f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
            } catch { return null; }
          })();
          const processedBearings = buildProcessedAbductionBearings(bearings, firstRulerName);
          if (!processedBearings.length) return '';
          const pls = f?.planets || {};
          const rows = processedBearings.slice(0,6).map((b)=>{
            const p = pls?.[b.planet] || {};
            const house = p?.house!=null? `H${p.house}` : 'H-';
            const sign = p?.sign || '-';
            const az = (b?.azimuth_deg!=null)? `${Number(b.azimuth_deg).toFixed(1)}°` : '-';
            const alt = (b?.altitude_deg!=null)? `${Number(b.altitude_deg).toFixed(1)}°` : '-';
            const w = (b?.weight!=null)? Number(b.weight).toFixed(2) : '-';
            return `<tr><td>${formatAbductionBearingRoleLabel(b)}</td><td>${b.planet||'-'}</td><td style=\"text-align:right\">${az}</td><td style=\"text-align:right\">${alt}</td><td>${house} ${sign}</td><td style=\"text-align:right\">${w}</td></tr>`;
          }).join('');
          return rows ? `<h2>Abduction Bearings</h2><table class=\"tbl\"><thead><tr><th>Role</th><th>Planet</th><th>Az</th><th>Alt</th><th>Pos</th><th>W</th></tr></thead><tbody>${rows}</tbody></table>` : '';
        } catch { return ''; }
      })();
      // Build tile-like sections (textual)
      const victimSec = (() => {
        try {
          const cusps = f?.house_cusps || [];
          const ascLon = Number(cusps?.[0]);
          const ascSign = isFinite(ascLon) ? signFromLon(ascLon) : '-';
          const rulers = f?.house_rulers || {};
          const firstRuler = f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
          const co = ['Moon', ...(caseType==='child'? ['Mercury']: []), ...(caseType==='adult_female'? ['Venus']: [])];
          const mi = f?.planets?.Moon || {};
          const mSign = mi?.sign || '-';
          const mDeg = isFinite(mi?.longitude) ? degreeTextFromLon(mi.longitude) : '-';
          const mHouse = mi?.house ?? '-';
          const voc = (()=>{ try { const mt = dash?.moon_timeline; return (mt && typeof mt.in_voc === 'boolean') ? mt.in_voc : Boolean((dash?.moon || f?.moon || {}).void_of_course); } catch{ return false; } })();
          const via = Boolean(mi?.via_combusta);
          // Malefic danger lines
          const a = f?.aspects || {};
          const mal = Object.entries(a).filter(([k,v])=> v && (k.startsWith('Moon_to_') || k.endsWith('_to_Moon')))
            .map(([k,v])=>{ const [p1,p2]=k.split('_to_'); const other=(p1==='Moon'? p2: p1); return { other, type: String(v.type||''), applying: v.applying===true }; })
            .filter(x=> (x.other==='Mars'||x.other==='Saturn') && (x.type==='square'||x.type==='opposition'))
            .map(x=> `${x.type} ${x.other}${x.applying? ' (app)':''}`);
          return `<h2>Victim Analysis</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>ASC Sign</td><td>${ascSign}</td></tr>
              <tr><td>Primary Ruler</td><td>${firstRuler||'-'}</td></tr>
              <tr><td>Co‑rulers</td><td>${co.join(', ')}</td></tr>
              <tr><td>Moon</td><td>${mSign} ${mDeg} (H${mHouse}) · VoC ${voc? 'Yes':'No'} · Via combusta ${via? 'Yes':'No'}</td></tr>
              <tr><td>Danger (malefics)</td><td>${mal.length? mal.join(' · '): '-'}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const perpSec = (() => {
        try {
          const rulers = f?.house_rulers || {};
          const seventhRuler = f?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
          const pl = f?.planets || {};
          const r = pl?.[seventhRuler] || {};
          const cusp7 = Number((f?.house_cusps||[])[6]);
          const cusp7Sign = isFinite(cusp7)? signFromLon(cusp7): '-';
          const cusp7Deg = isFinite(cusp7)? degreeTextFromLon(cusp7): '-';
          const h7List = Object.entries(pl).filter(([,p])=> p?.house===7).map(([n])=> n);
          const sign = r?.sign || '-'; const deg = isFinite(r?.longitude)? degreeTextFromLon(r.longitude): '-'; const house = r?.house ?? '-';
          const solar = dash?.features?.solar || f?.solar || {};
          const inSolar = (k, p) => Array.isArray(solar?.[k]) && solar[k].includes(p);
          const dignFlags = (() => { const raw=String(r?.essential_dignity_raw||'').toLowerCase(); const tags=new Set((Array.isArray(r?.dignities)? r.dignities: []).map(t=> String(t).toLowerCase())); const out=[]; if (raw.includes('domicile')||raw.includes('ruler')||tags.has('domicile')||tags.has('rulership')) out.push('Rulership'); if (raw.includes('exalt')||Array.from(tags).some(t=> t.includes('exalt'))) out.push('Exaltation'); if (Array.from(tags).some(t=> t.includes('triplicity'))) out.push('Triplicity'); if (Array.from(tags).some(t=> t.includes('term')||t.includes('bound'))) out.push('Term'); if (Array.from(tags).some(t=> t.includes('face')||t.includes('decan'))) out.push('Face'); if (raw.includes('detriment')||tags.has('detriment')) out.push('Detriment'); if (raw.includes('fall')||tags.has('fall')) out.push('Fall'); return out.length? out: ['Neutral']; })();
          const asp = f?.aspects || {};
          const collectBy = (planet) => Object.entries(asp)
            .filter(([k, v]) => v && (k.includes(`_to_${planet}`) || k.startsWith(`${planet}_to_`)))
            .map(([, v]) => ({ type: v?.type, applying: v?.applying }));
          const aspectBucket = (planet) => formatForensicAspectLabels(collectBy(planet));
          return `<h2>Perpetrator Signals</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>7th-house cusp</td><td>${cusp7Sign} ${cusp7Deg} | ruler ${seventhRuler||'-'}</td></tr>
              <tr><td>7th-house co-signifiers</td><td>${h7List.length? h7List.join(', '): '-'}</td></tr>
              <tr><td>Ruler placement</td><td>${sign} ${deg} (H${house})</td></tr>
              <tr><td>Dignity</td><td>${dignFlags.join(', ') || '-'}</td></tr>
              <tr><td>State</td><td>${r?.retrograde? 'Retrograde':'Direct'}${inSolar('cazimi', seventhRuler)? ' | Cazimi':''}${inSolar('combustion', seventhRuler)? ' | Combust':''}${inSolar('under_beams', seventhRuler)? ' | Under beams':''}</td></tr>
              <tr><td>Malefic/benefic contacts</td><td>Saturn: ${aspectBucket('Saturn')} | Mars: ${aspectBucket('Mars')} | Jupiter: ${aspectBucket('Jupiter')} | Venus: ${aspectBucket('Venus')}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const relationshipSec = (() => {
        try {
          const rulers = f?.house_rulers || {};
          const firstRuler = f?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
          const seventhRuler = f?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
          const sr = { Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter' };
          const exaltation = { Sun:'Aries', Moon:'Taurus', Mercury:'Virgo', Venus:'Pisces', Mars:'Capricorn', Jupiter:'Cancer', Saturn:'Libra' };
          const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
          const opp = (s) => signs[(signs.indexOf(s)+6)%12] || null;
          const triOf = (sign) => {
            if (!sign) return null;
            if (['Aries','Leo','Sagittarius'].includes(sign)) return 'Fire';
            if (['Taurus','Virgo','Capricorn'].includes(sign)) return 'Earth';
            if (['Gemini','Libra','Aquarius'].includes(sign)) return 'Air';
            if (['Cancer','Scorpio','Pisces'].includes(sign)) return 'Water';
            return null;
          };
          const planets = f?.planets || {};
          const victimSign = planets?.[firstRuler]?.sign; const perpSign = planets?.[seventhRuler]?.sign;
          const victimHouse = planets?.[firstRuler]?.house; const perpHouse = planets?.[seventhRuler]?.house;
          const recData = dash?.receptions || {};
          const mutual = Array.isArray(recData.mutual)? recData.mutual : [];
          const uni = Array.isArray(recData.top_unilateral)? recData.top_unilateral : [];
          const directVictRulesPerp = victimSign && sr[perpSign] === firstRuler;
          const directPerpRulesVict = perpSign && sr[victimSign] === seventhRuler;
          const isMutual = mutual.some(m => (m.p1===firstRuler && m.p2===seventhRuler) || (m.p1===seventhRuler && m.p2===firstRuler));
          const level3 = victimSign && perpSign && (triOf(victimSign) === triOf(perpSign));
          const perpExaltSign = exaltation[seventhRuler];
          const victExaltSign = exaltation[firstRuler];
          const level4_victim_in_exalt_of_perp = victimSign && (victimSign === perpExaltSign);
          const level4_perp_in_exalt_of_victim = perpSign && (perpSign === victExaltSign);
          const level4_victim_in_fall_of_perp = victimSign && (victimSign === opp(perpExaltSign));
          const level4_perp_in_fall_of_victim = perpSign && (perpSign === opp(victExaltSign));
          const houseFlags = [];
          if (victimHouse===1) houseFlags.push('Victim ruler in 1st');
          if (victimHouse===7) houseFlags.push('Victim ruler in 7th');
          if (victimHouse===4||victimHouse===10) houseFlags.push('Victim ruler in 4th/10th');
          if (perpHouse===1) houseFlags.push('Perp ruler in 1st');
          if (perpHouse===4||perpHouse===10) houseFlags.push('Perp ruler in 4th/10th');
          if (perpHouse===7) houseFlags.push('Perp ruler in 7th');
          const sameHouse = (victimHouse!=null && perpHouse!=null && victimHouse===perpHouse);
          if (sameHouse) houseFlags.push('Both rulers in same house');
          const aspMap = f?.aspects || {};
          const a = aspMap[`${firstRuler}_to_${seventhRuler}`] || aspMap[`${seventhRuler}_to_${firstRuler}`] || null;
          const aspType = a?.type || null;
          const aspectFlags = [];
          if (aspType) {
            const easy=['conjunction','trine','sextile']; const hard=['square','opposition'];
            if (easy.includes(aspType)) aspectFlags.push(`Harmonious (${aspType})`);
            if (hard.includes(aspType)) aspectFlags.push(`Stressful (${aspType})`);
            if (a?.applying===true) aspectFlags.push('Applying');
          } else { aspectFlags.push('No direct aspect'); }
          const relationshipRows = buildRelationshipDisplayRows({
            directVictRulesPerp,
            directPerpRulesVict,
            isMutual,
            level3,
            exaltationFallFlags: [
              level4_victim_in_exalt_of_perp ? 'victim in exaltation of perpetrator' : null,
              level4_perp_in_exalt_of_victim ? 'perpetrator in exaltation of victim' : null,
              level4_victim_in_fall_of_perp ? 'victim in fall of perpetrator' : null,
              level4_perp_in_fall_of_victim ? 'perpetrator in fall of victim' : null,
            ].filter(Boolean),
            houseConnections: houseFlags,
            aspectTies: aspectFlags,
          });
          const lines = [
            `Rulership links: ${relationshipRows.rulershipLinks}`,
            `Mutual reception: ${relationshipRows.mutualReception}`,
            `Shared triplicity: ${relationshipRows.sharedTriplicity}`,
            `Exaltation/fall ties: ${relationshipRows.exaltationFallTies}`,
            `House overlap: ${relationshipRows.houseOverlap}`,
            `Aspect ties: ${relationshipRows.aspectTies}`,
          ];
          return `<h2>Relationship Signals</h2><div class=\"text\">${lines.map(l=> `<div>${l}</div>`).join('')}</div>`;
        } catch { return ''; }
      })();

      const witnessSec = (() => {
        try {
          const pls = f?.planets || {};
          const houseList = (h)=> Object.entries(pls).filter(([,p])=> p?.house===h).map(([n])=> n);
          const mercuryHouse = pls?.Mercury?.house || '-';
          const witnesses = ['Mercury', ...houseList(3)];
          const associates = houseList(11);
          const hidden = [...houseList(6), ...houseList(12)];
          return `<h2>Witness & Accomplice</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>Mercury (witness)</td><td>H${mercuryHouse}</td></tr>
              <tr><td>3rd (neighbors/local)</td><td>${witnesses.join(', ')||'-'}</td></tr>
              <tr><td>11th (associates)</td><td>${associates.join(', ')||'-'}</td></tr>
              <tr><td>6th/12th (hidden)</td><td>${hidden.join(', ')||'-'}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const finalSec = (() => {
        try {
          const cusps = f?.house_cusps || [];
          const cusp4 = Number(cusps?.[3]);
          const icDeg = isFinite(cusp4) ? degreeTextFromLon(cusp4) : '-';
          const cusp4Sign = isFinite(cusp4) ? signFromLon(cusp4) : '-';
          const icDict = dash?.ic_sign_meanings || {};
          const icExpl = cusp4Sign && icDict?.[cusp4Sign]?.outcome;
          const ruler4 = f?.house_rulers?.['4'] || f?.house_rulers?.[4] || null;
          const ruler4House = ruler4 ? f?.planets?.[ruler4]?.house : null;
          const icRulerDict = dash?.ic_ruler_house_meanings || {};
          const icRulerExpl = (ruler4House != null) ? (icRulerDict?.[String(ruler4House)]?.outcome) : null;
          const planets = f?.planets || {};
          const in4All = Object.entries(planets).filter(([,p])=> p?.house===4).map(([n])=> n);
          return `<h2>Final outcome determination</h2>
            <table class=\"tbl\"><tbody>
              <tr><td>IC</td><td>${cusp4Sign} ${icDeg}${icExpl? ` - ${icExpl}`:''}</td></tr>
              <tr><td>IC ruler</td><td>${ruler4||'-'}${ruler4House? ` in H${ruler4House}`:''}${icRulerExpl? ` - ${icRulerExpl}`:''}</td></tr>
              <tr><td>Planets in 4th</td><td>${in4All.join(', ')||'-'}</td></tr>
            </tbody></table>`;
        } catch { return ''; }
      })();

      const css = `
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color: #111827; }
        .container { padding: 24px; }
        h1 { font-size: 20px; margin: 0 0 4px; }
        h2 { font-size: 14px; margin: 16px 0 4px; }
        .muted { color: #6b7280; font-size: 12px; }
        pre { white-space: pre-wrap; font-size: 12px; line-height: 1.5; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #fff; }
        .map { margin-top: 12px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
        .sep { height: 1px; background: #e5e7eb; margin: 12px 0; }
        .tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
        .tbl th, .tbl td { border: 1px solid #e5e7eb; padding: 6px 8px; }
        .tbl thead { background: #f8fafc; }
        .text div { margin: 4px 0; }
      `;
      const safeBrief = brief ? brief.replace(/</g,'&lt;') : '-';
      return `<!doctype html><html><head><meta charset=\"utf-8\" /><title>Forensic Report</title><style>${css}</style></head>
        <body><div class=\"container\">
          <h1>Forensic Report</h1>
          <div class=\"muted\">Generated ${ts}${caseHeader? ` · ${caseHeader}`:''}</div>
          <div class=\"sep\"></div>
          <h2>Summary</h2>
          <pre>${safeBrief}</pre>
          ${victimSec}
          ${perpSec}
          ${relationshipSec}
          ${witnessSec}
          ${finalSec}
          ${svg ? `<h2>Abduction Map</h2><div class=\"map\">${svg}</div>` : ''}
          ${bearingsTable}
        </div></body></html>`;
    } catch { return '<html><body>Error</body></html>'; }
  }
  const primaryRuler = features?.houses?.first_ruler || (ascSign ? signRuler[ascSign] : null);
  const coRulers = (() => {
    const list = ['Moon'];
    if (ascSign === 'Cancer') return list; // special case (avoid over-adding here; we will dedupe later)
    if (caseType === 'child' && !list.includes('Mercury')) list.push('Mercury');
    if (caseType === 'adult_female' && !list.includes('Venus')) list.push('Venus');
    return list;
  })();
  // Dominance helpers from API
  const domMap = (data?.dominance && data.dominance.planets) ? data.dominance.planets : {};
  const domInfo = (p) => (p && domMap && domMap[p]) ? domMap[p] : null;
  const dign = (pname) => {
    try { return Number(features?.planets?.[pname]?.dignity_score)||0; } catch { return 0; }
  };

  // Describe any aspects between victim ruler and malefics (Mars/Saturn), both directions
  const maleficThreatDetails = (pname) => {
    try {
      const a = features?.aspects || {};
      const keys = Object.keys(a).filter(k => k.startsWith(pname+"_to_") || k.endsWith("_to_"+pname));
      const out = [];
      for (const k of keys) {
        const rec = a[k] || {};
        const [p1, p2] = k.split('_to_');
        const other = (p1 === pname) ? p2 : p1;
        if (!['Mars','Saturn'].includes(other)) continue;
        const typ = String(rec.type || '').toLowerCase();
        if (!typ) continue;
        const app = rec.applying === true;
        const orb = (typeof rec.orb === 'number') ? `${Number(rec.orb).toFixed(1)}°` : null;
        out.push(`${other} ${typ}${app ? ' (app)' : ''}${orb ? ' · '+orb : ''}`);
      }
      return out;
    } catch { return []; }
  };
  const survival = (() => {
    return summarizeForensicSurvivalSignal({ forensicResult: data });
  })();

  return (
    <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-start justify-center p-4 overflow-auto">
      {/* Floating close button for the entire overlay */}
      <div className="absolute top-4 right-4">
        <div role="button" tabIndex={0} onClick={onClose}
             onKeyDown={(e)=>{ if (e.key==='Enter' || e.key===' ') { e.preventDefault(); onClose?.(); } }}
             className="text-[11px] px-2 py-0.5 border rounded bg-white/90 hover:bg-white cursor-pointer select-none shadow">Close</div>
      </div>
      <div className="w-full max-w-5xl space-y-4">

        {card('Directional Findings', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="border rounded p-2">
                  <div className="font-medium mb-1">Case Axes</div>
                  <div className="flex flex-wrap gap-1">
                    {replayAxes.length ? replayAxes.map((axis) => (
                      <span key={axis} className="text-[11px] px-2 py-0.5 rounded border border-zinc-300 bg-zinc-50">
                        {formatForensicDisplayLabel(axis)}
                      </span>
                    )) : <span className="text-xs text-zinc-500">-</span>}
                  </div>
                </div>
                <div className="border rounded p-2">
                  <div className="font-medium mb-1">Engine Categories</div>
                  <div className="flex flex-wrap gap-1">
                    {categoryEntries.length ? categoryEntries.map(([name, count]) => (
                      <span key={name} className="text-[11px] px-2 py-0.5 rounded border border-zinc-300 bg-white">
                        {name}: {count}
                      </span>
                    )) : <span className="text-xs text-zinc-500">-</span>}
                  </div>
                </div>
                <div className="border rounded p-2 md:col-span-2">
                  <div className="font-medium mb-1">Top Findings</div>
                  <div className="flex flex-wrap gap-1">
                    {rawFindings.length ? rawFindings.slice(0, 8).map((finding, idx) => (
                      <span
                        key={`${finding?.title || 'finding'}-${idx}`}
                        className="max-w-full min-w-0 whitespace-normal break-words text-[11px] leading-snug px-2 py-0.5 rounded border border-zinc-300 bg-white"
                      >
                        {cleanForensicDisplayText(finding?.title || '-')}
                      </span>
                    )) : <span className="text-xs text-zinc-500">-</span>}
                  </div>
                </div>
                <div className="border rounded p-2 md:col-span-2">
                  <div className="font-medium mb-1">Finding Notes</div>
                  <div className="space-y-2">
                    {rawFindings.length ? rawFindings.slice(0, 8).map((finding, idx) => {
                      const title = cleanForensicDisplayText(finding?.title || '-');
                      const rationale = cleanForensicDisplayText(finding?.rationale || '');
                      const isOpen = expandedFindingIndex === idx;
                      return (
                        <div key={`${title}-${idx}`} className="rounded border border-zinc-200 bg-white">
                          <button
                            type="button"
                            aria-expanded={isOpen ? 'true' : 'false'}
                            onClick={() => setExpandedFindingIndex(isOpen ? null : idx)}
                            className="w-full min-w-0 flex items-start gap-2 px-2 py-1.5 text-left hover:bg-zinc-50"
                          >
                            <span className="inline-block w-4 shrink-0 text-[11px] text-zinc-500">{isOpen ? '▾' : '▸'}</span>
                            <span className="min-w-0 whitespace-normal break-words text-[11px] leading-snug text-zinc-800">{title}</span>
                          </button>
                          {isOpen && (
                            <div className="border-t border-zinc-200 px-6 py-2 whitespace-normal break-words text-[11px] leading-snug text-zinc-600">
                              {rationale || 'No rationale supplied.'}
                            </div>
                          )}
                        </div>
                      );
                    }) : <div className="text-xs text-zinc-500">-</div>}
                  </div>
                </div>
              </div>
            </div>
          )
        ))}

        {card('Victim Analysis', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-[11px]">
                  <span className="px-2 py-0.5 border rounded">Asc Sign: {ascSign || '-'}</span>
                  <span className="px-2 py-0.5 border rounded">Primary Ruler: {primaryRuler || '-'}</span>
                  <span className="px-2 py-0.5 border rounded">Co-Rulers: {coRulers.join(', ')}</span>
                  <select value={caseType} onChange={e=>setCaseType(e.target.value)} className="px-2 py-0.5 border rounded">
                    <option value="general">General</option>
                    <option value="child">Child case</option>
                    <option value="adult_female">Adult female</option>
                  </select>
                </div>
                <div role="button" tabIndex={0}
                     onClick={()=> setAbductionMode(v=>!v)}
                     onKeyDown={(e)=>{ if (e.key==='Enter' || e.key===' '){ e.preventDefault(); setAbductionMode(v=>!v);} }}
                     className={`text-[11px] px-2 py-0.5 border rounded cursor-pointer select-none ${abductionMode? 'bg-zinc-900 text-white':'bg-white'}`}>Abduction View</div>
                <label className="flex items-center gap-1 text-[11px] ml-2">
                  <input type="checkbox" checked={includeRaw} onChange={e=>setIncludeRaw(e.target.checked)} />
                  <span>RAW</span>
                </label>
                <div role="button" tabIndex={0}
                     onClick={async ()=> { try { const txt = buildAIBrief(includeRaw); await navigator.clipboard.writeText(txt); setCopiedBrief(true); setTimeout(()=> setCopiedBrief(false), 2000);} catch(_){/*noop*/} }}
                     onKeyDown={async (e)=>{ if (e.key==='Enter' || e.key===' ') { e.preventDefault(); try { const txt = buildAIBrief(includeRaw); await navigator.clipboard.writeText(txt); setCopiedBrief(true); setTimeout(()=> setCopiedBrief(false), 2000);} catch(_){/*noop*/} } }}
                     className={`text-[11px] px-2 py-0.5 border rounded cursor-pointer select-none ${copiedBrief? 'bg-zinc-900 text-white':'bg-white'}`}>{copiedBrief? 'Copied' : 'AI Brief (Copy)'}</div>
                <button
                  type="button"
                  className="text-[11px] px-2 py-0.5 border rounded bg-white hover:bg-zinc-50"
                  onClick={async ()=>{
                    try {
                      const html = buildReportHTML();
                      if (window.electronAPI?.exportReport) {
                        const res = await window.electronAPI.exportReport({ html, pageSize: 'A4' });
                        if (res?.ok) { setAbdMsg(`Report saved: ${res.path}`); }
                        else { console.warn('Export failed:', res?.error); setAbdMsg('Export failed - trying browser print…'); }
                      }
                      if (!window.electronAPI?.exportReport) {
                        // Fallback: open in new tab and trigger print dialog
                        const w = window.open('', '_blank');
                        if (w && w.document) {
                          w.document.write(html);
                          w.document.close();
                          setTimeout(()=> { try { w.focus(); w.print(); } catch(_){} }, 250);
                          setAbdMsg('Opened browser print dialog - choose "Save as PDF"');
                        } else {
                          setAbdMsg('Unable to open print dialog');
                        }
                      }
                    } catch (e) { console.warn('Export error', e); }
                  }}
                >Export PDF</button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="border rounded p-2">
                  <div className="font-medium mb-1">Victim Identification</div>
                  <div className="text-xs text-zinc-600">Primary ruler and co-rulers per case profile.</div>
                  <div className="mt-1 text-xs">Angular rulers: {[primaryRuler, ...coRulers].filter(Boolean).filter((p)=>Boolean(features?.planets?.[p]?.angular)).join(', ') || '-'}</div>
                  <div className="mt-1 text-xs">Primary ruler dominance: {(() => { const d = domInfo(primaryRuler); return d ? `${d.score} (${d.level})` : '-'; })()}</div>
                  {(() => {
                    try {
                      const vHouseGroup = (h) => { const n=Number(h); if ([1,4,7,10].includes(n)) return 'Angular'; if ([2,5,8,11].includes(n)) return 'Succedent'; return 'Cadent'; };
                      const mi = features?.planets?.['Moon'] || {};
                      const mLon = mi?.longitude; const mSign = mi?.sign || '-';
                      const mDeg = isFinite(mLon) ? degreeTextFromLon(mLon) : '-';
                      const mHouse = mi?.house;
                      const mt = data?.moon_timeline;
                      const voc = (mt && typeof mt.in_voc === 'boolean')
                        ? mt.in_voc
                        : Boolean((data?.moon || features?.moon || {}).void_of_course);
                      const via = Boolean(mi?.via_combusta);
                      const a = features?.aspects || {};
                      const mAspects = Object.entries(a).filter(([k,v])=> v && (k.startsWith('Moon_to_') || k.endsWith('_to_Moon')))
                        .map(([k,v])=> { const [p1,p2]=k.split('_to_'); const other = (p1==='Moon'? p2 : p1); return { other, type: String(v.type||''), applying: v.applying===true }; });
                      const malHard = mAspects.filter(x=> (x.other==='Mars'||x.other==='Saturn') && (x.type==='square'||x.type==='opposition'))
                        .map(x=> `${x.type} ${x.other}${x.applying? ' (app)':''}`);
                      const toPrimary = mAspects.find(x=> x.other===primaryRuler);
                      return (
                        <div className="mt-2 pt-2 border-t border-zinc-200">
                          <div className="font-medium mb-1">Moon (universal co‑ruler)</div>
                          <div className="text-xs">Position: {mSign} {mDeg} (H{mHouse ?? '-'} · {vHouseGroup(mHouse)})</div>
                          <div className="text-xs">Dignity score: {dign('Moon')}</div>
                          <div className="text-xs">Conditions: VoC {voc? 'Yes':'No'} · Via combusta {via? 'Yes':'No'}</div>
                          <div className="text-xs">Danger (malefics): {malHard.length? malHard.join(' · ') : '-'}</div>
                          <div className="text-xs">Aspect to primary ruler: {toPrimary? `${toPrimary.type}${toPrimary.applying? ' (app)':''}` : '-'}</div>
                        </div>
                      );
                    } catch { return null; }
                  })()}
                </div>
                <div className="border rounded p-2">
                  <div className="font-medium mb-1">Victim Location Matrix</div>
                  <ul className="text-xs list-disc ml-4 space-y-1">
                    <li>1st House: immediate surroundings (ASC sign {ascSign || '-'}).</li>
                    <li>Angular houses: indicate victim’s control level (angular rulers listed above).</li>
                    <li>Victim significators: {Array.isArray(survival.victimSignificators) && survival.victimSignificators.length ? survival.victimSignificators.join(' · ') : [primaryRuler, ...coRulers].filter(Boolean).join(' · ') || '-'}</li>
                      <li>
                        Survivability signal:{' '}
                        <span className={survival.level==='Higher'?'text-emerald-700':(survival.level==='Lower'?'text-rose-700':'text-amber-700')}>
                          {survival.level}
                        </span>
                        {typeof survival.score === 'number' ? <span className="text-zinc-500"> ({survival.score >= 0 ? '+' : ''}{survival.score})</span> : null}
                        {survival.outcomeBand ? <span className="text-zinc-500"> · {formatSurvivabilityBandLabel(survival.outcomeBand)}</span> : null}
                        {survival.fatalOverride ? <span className="text-zinc-500"> (fatal pressure dominates)</span> : null}
                      </li>
                      {survival.breakdown ? (
                        <li>
                          {(() => {
                            const accidental = Number(survival.breakdown.accidental || 0);
                            const recoverySupport = Number(survival.breakdown.recovery_support || 0);
                            return (
                              <>
                          Basis: vitality {survival.breakdown.vitality >= 0 ? '+' : ''}{survival.breakdown.vitality} ·
                          accidental {accidental >= 0 ? '+' : ''}{accidental} ·
                          support {survival.breakdown.support >= 0 ? '+' : ''}{survival.breakdown.support} ·
                          recovery support {recoverySupport >= 0 ? '+' : ''}{recoverySupport} ·
                          Moon {survival.breakdown.moon >= 0 ? '+' : ''}{survival.breakdown.moon} ·
                          danger {survival.breakdown.danger} ·
                          fatal pressure {survival.breakdown.fatal_pressure}
                              </>
                            );
                          })()}
                        </li>
                      ) : null}
                    <li>Aspects to malefics: {(() => {
                      const vics = [primaryRuler, ...coRulers].filter(Boolean);
                      const parts = [];
                      vics.forEach(v => {
                        const det = maleficThreatDetails(v);
                        if (det.length) parts.push(`${v}: ${det.join(', ')}`);
                      });
                      return parts.join(' · ') || '-';
                    })()}</li>
                    {survival.note ? <li>Read: {survival.note}</li> : null}
                  </ul>
                </div>
              </div>
            </div>
          )
        ))}
        {abductionMode && card('Abduction Cues', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {/* Origin input and fetch controls */}
              <div className="text-[11px] text-zinc-600">
                Use the last known point, seizure point, or reporting origin as the map anchor.
              </div>
              <div className="flex items-end gap-2 text-xs">
                <div>
                  <div className="text-[11px] text-zinc-600">Origin Latitude</div>
                  <input value={originLat} onChange={e=>setOriginLat(e.target.value)} className="px-2 py-1 border rounded w-40" placeholder="e.g., 40.7608" inputMode="decimal" />
                </div>
                <div>
                  <div className="text-[11px] text-zinc-600">Origin Longitude</div>
                  <input value={originLon} onChange={e=>setOriginLon(e.target.value)} className="px-2 py-1 border rounded w-40" placeholder="e.g., -111.8910" inputMode="decimal" />
                </div>
                <button type="button" className={`px-2 py-1 rounded border ${fetchingAbd? 'bg-zinc-200':'hover:bg-zinc-50'}`} onClick={async()=>{
                  const latStr = normalizeCoordinateInput(originLat); const lonStr = normalizeCoordinateInput(originLon);
                  const lat = parseFloat(latStr); const lon = parseFloat(lonStr);
                  if (!isFinite(lat)||!isFinite(lon)) { setAbdMsg('Invalid coordinates. Example: 40.7608, -111.8910'); return; }
                  console.log('[Abduction] Fetch click with origin:', lat, lon);
                  setFetchingAbd(true);
                  setAbdMsg('Fetching abduction map…');
                  try { await fetchForensic({ abduction: true, origin: `${lat},${lon}`, line_zones: true }); }
                  catch(_){}
                  finally { setFetchingAbd(false); }
                }}>{fetchingAbd? 'Fetching…':'Load Abduction Map'}</button>
              </div>
              {abdMsg && <div className="text-[11px] text-zinc-600">{abdMsg}</div>}

              {(() => {
                try {
                  const summary = buildAbductionCueSummary({ data, features });
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="border rounded p-2">
                          <div className="font-medium mb-1">Scene Signals</div>
                          <div className="text-xs">Victim signal: <span className="font-semibold">{summary.victimAnchor}</span></div>
                          <div className="text-xs">Movement signal: {summary.movementAnchor}</div>
                          {summary.primaryHouseCues.length > 0 && (
                            <div className="text-xs mt-1">Primary place cues: {summary.primaryHouseCues.join(' · ')}</div>
                          )}
                          {summary.primarySignCues.length > 0 && (
                            <div className="text-xs">Scene modifiers: {summary.primarySignCues.join(' · ')}</div>
                          )}
                          {summary.movementCues.length > 0 && (
                            <div className="text-xs">Route and movement cues: {summary.movementCues.join(' · ')}</div>
                          )}
                        </div>
                        <div className="border rounded p-2">
                          <div className="font-medium mb-1">Access and Distance</div>
                          <div className="text-xs">Tier: <span className="font-semibold">{summary.accessProfile.title}</span></div>
                          {summary.accessNotes.length > 0 && (
                            <div className="text-xs mt-1">Access notes: {summary.accessNotes.join(' · ')}</div>
                          )}
                          {summary.distanceCues.length > 0 && (
                            <div className="text-xs">Distance read: {summary.distanceCues.join(' · ')}</div>
                          )}
                          {summary.modifiers.length > 0 && (
                            <div className="text-xs">Context modifiers: {summary.modifiers.join(' · ')}</div>
                          )}
                        </div>
                      {/* Combo Matches panel removed per request */}
                    </div>
                  );
                } catch(_) { return <div className="text-xs text-zinc-500">Unavailable</div>; }
              })()}
            </div>
          )
        ))}

        {abductionMode && card('Abduction Map', (
          (() => {
            const abd = data?.abduction_map || {};
            const origin = abd.origin || {};
            let lat = Number(origin.lat); let lon = Number(origin.lon);
            if (!isFinite(lat) || !isFinite(lon)) {
              const li = parseFloat(originLat); const lo = parseFloat(originLon);
              if (isFinite(li) && isFinite(lo)) { lat = li; lon = lo; }
            }
            // Raw bearings from backend
            const bearings = Array.isArray(abd.bearings)? abd.bearings : [];
            // Replace 'Planet in 7th' with '1st ruler' in both sources list and map
            const firstRulerName = (()=>{
              try {
                const rulers = features?.house_rulers || {};
                return features?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
              } catch { return null; }
            })();
            const processedBearings = buildProcessedAbductionBearings(bearings, firstRulerName);
            const hasOrigin = isFinite(lat) && isFinite(lon);
            if (!hasOrigin) return <div className="text-sm text-zinc-500">Enter an origin point above, then load the map.</div>;
            const MapClick = ({ onPick }) => { useMapEvents({ click(e){ try { onPick && onPick(e.latlng); } catch(_){} } }); return null; };
            const MapHover = () => { useMapEvents({ mousemove(e){ try { setMapHover({ lat: e.latlng.lat, lon: e.latlng.lng }); } catch(_){} } }); return null; };
            const dest = (lat0, lon0, brgDeg, distKm) => {
              const R = 6371.0; const d = distKm / R; const br = (brgDeg*Math.PI/180);
              const la1 = lat0*Math.PI/180; const lo1 = lon0*Math.PI/180;
              const la2 = Math.asin(Math.sin(la1)*Math.cos(d) + Math.cos(la1)*Math.sin(d)*Math.cos(br));
              const lo2 = lo1 + Math.atan2(Math.sin(br)*Math.sin(d)*Math.cos(la1), Math.cos(d)-Math.sin(la1)*Math.sin(la2));
              return [la2*180/Math.PI, ((lo2*180/Math.PI)+540)%360-180];
            };
            const bearingLine = (az, km) => [ [lat, lon], dest(lat, lon, az, km) ];
            const toRad = (v)=> v*Math.PI/180;
            const toDeg = (v)=> v*180/Math.PI;
            const normalize360 = (x)=> (x%360+360)%360;
            const distKm = (la1,lo1,la2,lo2)=>{
              const R=6371.0; const dLat=toRad(la2-la1); const dLon=toRad(lo2-lo1);
              const a = Math.sin(dLat/2)**2 + Math.cos(toRad(la1))*Math.cos(toRad(la2))*Math.sin(dLon/2)**2;
              return R*2*Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            };
            const bearingDeg = (la1,lo1,la2,lo2)=>{
              const dLon=toRad(lo2-lo1); const lat1=toRad(la1); const lat2=toRad(la2);
              const y=Math.sin(dLon)*Math.cos(lat2);
              const x=Math.cos(lat1)*Math.sin(lat2)-Math.sin(lat1)*Math.cos(lat2)*Math.cos(dLon);
              return normalize360(toDeg(Math.atan2(y,x)));
            };
            const toCardinal16 = (b)=>{
              const dirs=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
              const idx=Math.round(normalize360(b)/22.5)%16; return dirs[idx];
            };
            return (
              <div className="space-y-2">
                <div className="h-96 w-full border rounded overflow-hidden relative">
                  <MapContainer center={[lat, lon]} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
                    <MapClick onPick={(ll)=>{ try { setOriginLat(String(ll.lat.toFixed(5))); setOriginLon(String(ll.lng.toFixed(5))); } catch(_){} }} />
                    <MapHover />
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors"/>
                    <Marker position={[lat, lon]}><Popup>Origin<br/>{lat.toFixed(5)}, {lon.toFixed(5)}</Popup></Marker>
                    <Circle center={[lat, lon]} radius={3000} pathOptions={{ color:'#22c55e', fillOpacity:0.05 }} />
                    <Circle center={[lat, lon]} radius={12000} pathOptions={{ color:'#eab308', fillOpacity:0.03 }} />
                    <Circle center={[lat, lon]} radius={40000} pathOptions={{ color:'#ef4444', fillOpacity:0.02 }} />
                    {(() => {
                      const drawAzimuth = (bearing) => {
                        try {
                          const az = Number(bearing?.azimuth_deg);
                          if (!isFinite(az)) return null;
                          const alt = Number(bearing?.altitude_deg);
                          if (flipSubHorizon && isFinite(alt) && alt < 0) return (az + 180) % 360;
                          return az;
                        } catch { return null; }
                      };
                      return processedBearings.slice(0,6).map((b,i)=> {
                        const azToDraw = drawAzimuth(b);
                        if (azToDraw == null) return null;
                        const style = getAbductionRoleStyle(b?.role);
                        return (
                          <Polyline
                            key={`b${i}`}
                            positions={bearingLine(azToDraw, 40)}
                            pathOptions={{
                              color: style.color,
                              dashArray: style.dashArray || undefined,
                              weight: style.weight,
                              opacity: style.opacity,
                              lineCap: 'round',
                              lineJoin: 'round',
                            }}
                          />
                        );
                      });
                    })()}
                    {/* Zones removed */}
                  </MapContainer>
                  <div className="absolute top-2 right-2 z-[1001] pointer-events-none bg-white/90 backdrop-blur rounded border px-2 py-1 text-[11px] space-y-0.5 shadow">
                    {(() => { try {
                      const ml = mapHover; const has = ml && isFinite(ml.lat) && isFinite(ml.lon);
                      const d = has ? (function(){ const R=6371.0; const dLat=(ml.lat-lat)*Math.PI/180; const dLon=(ml.lon-lon)*Math.PI/180; const a = Math.sin(dLat/2)**2 + Math.cos(lat*Math.PI/180)*Math.cos(ml.lat*Math.PI/180)*Math.sin(dLon/2)**2; return R*2*Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); })() : null;
                      const brg = has ? (function(){ const dLon=(ml.lon-lon)*Math.PI/180; const lat1=lat*Math.PI/180; const lat2=ml.lat*Math.PI/180; const y=Math.sin(dLon)*Math.cos(lat2); const x=Math.cos(lat1)*Math.sin(lat2)-Math.sin(lat1)*Math.cos(lat2)*Math.cos(dLon); const deg=(Math.atan2(y,x)*180/Math.PI); const n=((deg%360)+360)%360; return n; })() : null;
                      const dirs=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
                      const card = (brg!=null)? dirs[Math.round(((brg%360)+360)%360/22.5)%16] : null;
                      return (
                        <>
                          <div>Cursor: {has? `${ml.lat.toFixed(5)}, ${ml.lon.toFixed(5)}` : '-'}</div>
                          <div>From origin: {has? `${d.toFixed(1)} km` : '-'}{has? ` · ${Math.round(brg)}° ${card}`: ''}</div>
                        </>
                      );
                    } catch(_) { return <div>-</div>; } })()}
                    {/* Legend */}
                    <div className="mt-1 pt-1 border-t border-zinc-200">
                      <div className="text-[10px] text-zinc-600">Legend</div>
                      {(() => {
                        const lineStyle = (s) => {
                          const base = { display: 'inline-block', width: '22px', height: '0px', marginRight: '6px' };
                          if (!s?.dashArray) return { ...base, borderTop: `2px solid ${s.color}` };
                          if (s.dashArray === '1 4') return { ...base, borderTop: `2px dotted ${s.color}` };
                          return { ...base, borderTop: `2px dashed ${s.color}` };
                        };
                        return (
                          <div className="space-y-0.5">
                            {getAbductionLegendEntries().map((e) => (
                              <div key={e.role} className="flex items-center">
                                <span style={lineStyle(e.style)} />
                                <span>{e.legendLabel}</span>
                              </div>
                            ))}
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>
                {/* Bearing sources list */}
                <div className="text-xs">
                  <div className="font-medium mb-1">Bearing Sources</div>
                  <div className="mb-1 flex items-center gap-2">
                    <label className="flex items-center gap-1">
                      <input type="checkbox" checked={!!showBackAz} onChange={(e)=> setShowBackAz(e.target.checked)} />
                      <span className="text-[11px]">Show back-azimuth (+180°)</span>
                    </label>
                    <label className="flex items-center gap-1">
                      <input type="checkbox" checked={!!flipSubHorizon} onChange={(e)=> setFlipSubHorizon(e.target.checked)} />
                      <span className="text-[11px]">Pro convention (flip sub-horizon)</span>
                    </label>
                  </div>
                  {(() => { try {
                    const pls = features?.planets || {};
                    const norm360 = (x)=> (x%360+360)%360;
                    const pad2 = (n)=> String(n).padStart(2,'0');
                    const pad3 = (n)=> String(n).padStart(3,'0');
                    const dmsCard4 = (az)=> {
                      if (az==null || !isFinite(az)) return '-';
                      let a = norm360(Number(az));
                      let d = Math.floor(a);
                      let mFloat = (a - d) * 60;
                      let m = Math.floor(mFloat);
                      let s = Math.round((mFloat - m) * 60);
                      if (s === 60) { s = 0; m += 1; }
                      if (m === 60) { m = 0; d += 1; }
                      if (d === 360) d = 0;
                      const card = (ang)=> {
                        const x = norm360(ang);
                        if (x>=45 && x<135) return 'E';
                        if (x>=135 && x<225) return 'S';
                        if (x>=225 && x<315) return 'W';
                        return 'N';
                      };
                      return `${pad3(d)} ${pad2(m)} ${pad2(s)} ${card(a)}`;
                    };
                    // Quadrantal N/S offset format (common in other software): angle measured from nearest N/S axis
                    const dmsNS = (az)=>{
                      if (az==null || !isFinite(az)) return '-';
                      const a = norm360(Number(az));
                      let off, letter;
                      if (a>=90 && a<270) { // South hemisphere
                        letter = 'S';
                        off = Math.abs(a - 180);
                      } else { // North hemisphere
                        letter = 'N';
                        // offset from North (0 or 360)
                        off = (a<=180)? a : (360 - a);
                      }
                      let d = Math.floor(off);
                      let mFloat = (off - d) * 60;
                      let m = Math.floor(mFloat);
                      let s = Math.round((mFloat - m) * 60);
                      if (s === 60) { s = 0; m += 1; }
                      if (m === 60) { m = 0; d += 1; }
                      if (d === 360) d = 0;
                      return `${pad2(d)} ${pad2(m)} ${pad2(s)} ${letter}`;
                    };
                    const items = processedBearings.slice(0,6).map((b,i)=> {
                      const inf = pls?.[b.planet] || {};
                      const sign = inf?.sign || '-';
                      const house = (inf?.house!=null)? `H${inf.house}` : 'H-';
                      const azNum = (b?.azimuth_deg!=null)? Number(b.azimuth_deg) : null;
                      const az = (azNum!=null)? `${azNum.toFixed(1)}°` : '-';
                      const alt = (b?.altitude_deg!=null)? `${Number(b.altitude_deg).toFixed(1)}°` : '-';
                      const w = (b?.weight!=null)? Number(b.weight).toFixed(2) : '-';
                      const dms = dmsCard4(azNum);
                      const qns = dmsNS(azNum);
                      let extra = null;
                      if (showBackAz) {
                        const back = (azNum!=null)? ( (azNum + 180) % 360 ) : null;
                        const backDms = dmsCard4(back);
                        const backQns = dmsNS(back);
                        const backDec = (back!=null)? `${back.toFixed(1)}°` : '-';
                        extra = <> · back 180° {backDec} · {backDms} · NS {backQns}</>;
                      }
                      return <li key={i}>{formatAbductionBearingRoleLabel(b)}: {b.planet} - {az} (alt {alt}) · {house} {sign} · w={w} · {dms} · NS {qns}{extra}</li>;
                    });
                    return (
                      <ul className="list-disc ml-4 space-y-0.5">{items.length? items : <li>-</li>}</ul>
                    );
                  } catch(_) { return <div>-</div>; } })()}
                </div>
              </div>
            );
          })()
        ))}

        {card('Perpetrator Analysis', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {(() => {
                const rulers = features?.house_rulers || {};
                const seventhRuler = features?.houses?.seventh_ruler || rulers['7'] || rulers[7] || null;
                const firstRuler = features?.houses?.first_ruler || rulers['1'] || rulers[1] || null;
                const seventhHousePlanets = Object.entries(features?.planets||{})
                  .filter(([,p]) => (p?.house===7))
                  .map(([name]) => name);
                const rulerInfo = features?.planets?.[seventhRuler] || {};
                const asp = features?.aspects || {};
                const rAspects = [];
                Object.entries(asp).forEach(([k,v])=>{
                  if (!v) return;
                  if (k.startsWith(`${seventhRuler}_to_`) || k.endsWith(`_to_${seventhRuler}`)) {
                    rAspects.push({ key:k, ...v });
                  }
                });
                const degFlags = [];
                if (rulerInfo.anaretic) degFlags.push('Anaretic');
                if (rulerInfo.ingress) degFlags.push('Ingress');
                if (rulerInfo.middegree) degFlags.push('Mid-degree');
                if (rulerInfo.via_combusta) degFlags.push('Via combusta');
                // Integer degree helper for fallback display
                const degInt = (() => {
                  try {
                    if (typeof rulerInfo?.degree_in_sign === 'number') return Math.round(rulerInfo.degree_in_sign);
                    if (isFinite(rulerInfo?.longitude)) return Math.round(((Number(rulerInfo.longitude)%30)+30)%30);
                  } catch(_) {}
                  return null;
                })();
                // Degree specials from knowledge dictionary
                const degSpecialHits = (() => {
                  try {
                    const dict = data?.degree_special || {};
                    const s = rulerInfo?.sign; if (!s) return [];
                    let degIn = null;
                    if (typeof rulerInfo?.degree_in_sign === 'number') degIn = rulerInfo.degree_in_sign;
                    else if (isFinite(rulerInfo?.longitude)) degIn = ((Number(rulerInfo.longitude)%30)+30)%30;
                    if (degIn == null) return [];
                    const rounded = Math.round(Number(degIn));
                    const out = [];
                    const specials = dict?.special || {};
                    Object.entries(specials).forEach(([key, val])=>{
                      try {
                        const parts = String(key).split('_');
                        const signName = parts[0];
                        const degNum = Number(parts[1]);
                        if (signName === s && degNum === rounded) {
                          out.push(val?.label || key);
                        }
                      } catch(_){}
                    });
                    const sd = (dict?.sign_degrees || {})[s];
                    if (Array.isArray(sd)) {
                      sd.forEach(entry => {
                        try {
                          const arr = Array.isArray(entry?.degree) ? entry.degree : [];
                          if (arr.includes(rounded)) {
                            const kws = Array.isArray(entry?.keywords) ? entry.keywords : [];
                            if (kws.length) out.push(kws.slice(0,3).join('/'));
                          }
                        } catch(_){}
                      });
                    }
                    return out;
                  } catch(_) { return []; }
                })();
                const collectBy = (planet) => rAspects
                  .filter(a => (a.key.includes(`_to_${planet}`) || a.key.startsWith(`${planet}_to_`)))
                  .map(a => ({ type: a?.type, applying: a?.applying }));
                const aspectBucket = (planet) => formatForensicAspectLabels(collectBy(planet));
                const bpf = { Mars: collectBy('Mars'), Saturn: collectBy('Saturn'), Neptune: collectBy('Neptune'), Pluto: collectBy('Pluto') };
                const fsRaw = Array.isArray(features?.fixed_stars_list)
                  ? features.fixed_stars_list
                  : (Array.isArray(features?.fixed_stars) ? features.fixed_stars : (features?.fixed_stars ? Object.values(features.fixed_stars) : []));
                const fsSunMoon = fsRaw.filter(h=> h?.target_type==='planet' && (h?.target==='Sun' || h?.target==='Moon'));
                const fsCusps = fsRaw.filter(h=> h?.target_type==='cusp');
                const fsDict = data?.fixed_star_meanings || {};
                const fsDescribe = (hit) => {
                  try {
                    const nm = hit?.name; const tgt = hit?.target; if (!nm) return null;
                    const entry = fsDict?.[nm] || fsDict?.[String(nm).trim()] || null;
                    const kw = entry?.forensic || entry?.meaning || '';
                    return `${nm}↔${tgt}${kw? ` - ${kw}`:''}`;
                  } catch(_) { return `${hit?.name||''}↔${hit?.target||''}`; }
                };
                const cusp7 = Number((features?.house_cusps||[])[6]);
                const cusp7Sign = isFinite(cusp7) ? signFromLon(cusp7) : '-';
                const cusp7Deg = isFinite(cusp7) ? degreeTextFromLon(cusp7) : '-';

                // Helpers
                const houseGroup = (h) => {
                  const n = Number(h);
                  if ([1,4,7,10].includes(n)) return 'Angular';
                  if ([2,5,8,11].includes(n)) return 'Succedent';
                  return 'Cadent';
                };
                // Derived houses from 7th perspective - helper used by alternates and summary
                const planetsByHouse = (h)=> Object.entries(features?.planets||{}).filter(([,p])=> p?.house===h).map(([n])=> n);
                const solar = data?.features?.solar || features?.solar || {};
                const inSolar = (k, p) => Array.isArray(solar?.[k]) && solar[k].includes(p);
                const dignFlags = (() => {
                  const raw = String(rulerInfo?.essential_dignity_raw||'').toLowerCase();
                  const tags = new Set((Array.isArray(rulerInfo?.dignities)? rulerInfo.dignities: []).map(t=> String(t).toLowerCase()));
                  const out = [];
                  if (raw.includes('domicile') || raw.includes('ruler') || tags.has('domicile') || tags.has('rulership')) out.push('Rulership');
                  if (raw.includes('exalt') || Array.from(tags).some(t=> t.includes('exalt'))) out.push('Exaltation');
                  if (Array.from(tags).some(t=> t.includes('triplicity'))) out.push('Triplicity');
                  if (Array.from(tags).some(t=> t.includes('term')||t.includes('bound'))) out.push('Term');
                  if (Array.from(tags).some(t=> t.includes('face')||t.includes('decan'))) out.push('Face');
                  if (raw.includes('detriment') || tags.has('detriment')) out.push('Detriment');
                  if (raw.includes('fall') || tags.has('fall')) out.push('Fall');
                  if (out.length===0) out.push('Neutral');
                  return out;
                })();
                const aspectTo = (target) => {
                  if (!target) return [];
                  const out = [];
                  Object.entries(asp).forEach(([k,v])=>{
                    if (!v) return;
                    if (k === `${seventhRuler}_to_${target}` || k === `${target}_to_${seventhRuler}`) {
                      out.push(`${v.type||''}${v.applying? ' (app)': ''}`);
                    }
                  });
                  return out;
                };
                const chainFrom = (planet) => {
                  try {
                    if (!planet) return [];
                    const sr = { Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter' };
                    const seen = new Set([planet]);
                    const chain = [planet];
                    let current = planet;
                    for (let i=0;i<8;i++) {
                      const info = features?.planets?.[current];
                      const s = info?.sign; if (!s) break;
                      const disp = sr[s]; if (!disp) break;
                      // Stop before adding if it would duplicate/self-dispose
                      if (seen.has(disp)) break;
                      chain.push(disp);
                      seen.add(disp);
                      current = disp;
                    }
                    return chain;
                  } catch { return [planet]; }
                };
                const dispChain = chainFrom(seventhRuler);
                const mutualReception = (dispChain.length>=3 && dispChain[2]===dispChain[0]) || false;
                const lm = data?.light_mediation || {};
                const translOrCollect = (() => {
                  try {
                    if (lm?.translation) return `Translation${lm?.translator? ` via ${lm.translator}`:''}`;
                    if (lm?.collection) return `Collection${lm?.collector? ` by ${lm.collector}`:''}`;
                    return '-';
                  } catch(_) { return '-'; }
                })();

                // Alternates based on context cues - compute with simple reasons
                const alt12Why = [];
                if (rulerInfo?.house === 12) alt12Why.push('ruler in H12');
                if (features?.houses?.emphasis12_strong) alt12Why.push('12th emphasis');
                const alt12 = alt12Why.length > 0;

                const alt5Why = [];
                if (rulerInfo?.house === 5) alt5Why.push('ruler in H5');
                const h5p = planetsByHouse(5);
                if (h5p.length >= 2) alt5Why.push('H5 emphasis');
                if (collectBy('Venus').length > 0 || (features?.planets?.Venus?.house === 5)) alt5Why.push('Venus link');
                const alt5 = alt5Why.length > 0;

                const alt10Why = [];
                if (rulerInfo?.house === 10) alt10Why.push('ruler in H10');
                const h10p = planetsByHouse(10);
                if (h10p.length >= 2) alt10Why.push('H10 emphasis');
                const satDom = domInfo('Saturn');
                if ((features?.planets?.Saturn?.angular === true) || (satDom && (satDom.level === 'Highly Dominant' || satDom.level === 'Extremely Dominant'))) alt10Why.push('Saturn/authority');
                const alt10 = alt10Why.length > 0;

                const derived = {
                  money: { house: 8, planets: planetsByHouse(8) },
                  home: { house: 10, planets: planetsByHouse(10) },
                  comms: { house: 9, planets: planetsByHouse(9) },
                  friends: { house: 5, planets: planetsByHouse(5) },
                };
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Perpetrator Signals</div>
                      <div className="text-xs">7th-house cusp: {cusp7Sign} {cusp7Deg} | ruler <span className="font-semibold">{seventhRuler || '-'}</span></div>
                      <div className="text-xs">7th-house co-signifiers: {seventhHousePlanets.length? seventhHousePlanets.join(', '): '-'}</div>
                      <div className="text-xs">Ruler placement: {(() => { const lon = rulerInfo?.longitude; const s = rulerInfo?.sign || '-'; const deg = isFinite(lon)? degreeTextFromLon(lon) : '-'; const h = rulerInfo?.house ?? '-'; return `${s} ${deg} (H${h} | ${houseGroup(h)})`; })()}</div>
                      <div className="text-xs">Dignity: {dignFlags.join(', ') || '-'}</div>
                      <div className="text-xs">State: {rulerInfo?.retrograde? 'Retrograde' : 'Direct'}{inSolar('cazimi', seventhRuler)? ' | Cazimi':''}{inSolar('combustion', seventhRuler)? ' | Combust':''}{inSolar('under_beams', seventhRuler)? ' | Under beams':''}</div>
                      <div className="text-xs">Malefic/benefic contacts: Saturn: {aspectBucket('Saturn')} | Mars: {aspectBucket('Mars')} | Jupiter: {aspectBucket('Jupiter')} | Venus: {aspectBucket('Venus')}</div>
                      {(() => {
                        // Applying aspects & timing (from horary perfections)
                        try {
                          const fmtDur = (days) => {
                            if (days == null || !isFinite(days)) return null;
                            const d = Math.floor(days);
                            const h = Math.round((days - d) * 24);
                            if (d > 0) return `${d}d${h? ` ${h}h`: ''}`;
                            return `${h}h`;
                          };
                          const ap = rAspects
                            .filter(a => a?.applying === true)
                            .map(a => ({...a, t: (a?.time_to_perfection != null ? Number(a.time_to_perfection) : Infinity)}))
                            .sort((a,b)=> a.t - b.t)
                            .slice(0,4)
                            .map(a => {
                              const [p1,p2] = a.key.split('_to_');
                              const other = (p1===seventhRuler ? p2 : p1);
                              const t = fmtDur(a.t);
                              const within = (a?.perfection_within_sign === true ? '[check]' : (a?.perfection_within_sign === false ? '✗' : ''));
                              const segs = [`${a.type||''} ${other}`];
                              if (t) segs.push(`in ${t}`);
                              if (within) segs.push(`(within sign ${within})`);
                              return segs.join(' ');
                            });
                          return (
                            <div className="text-xs">Applying contacts: {ap.length? ap.join(' | '): '-'}</div>
                          );
                        } catch(_) { return null; }
                      })()}
                      <div className="text-xs">Degree markers: {(() => { const parts = [...degFlags]; if (degSpecialHits.length) parts.push(...degSpecialHits); if (parts.length) return parts.join(' | '); const s=rulerInfo?.sign||'-'; return degInt!=null? `${s} ${degInt}°` : '-'; })()}</div>
                      {(() => {
                        const segs = [];
                        if (alt12) segs.push(`12th - hidden enemy${alt12Why.length? ` (${alt12Why.join(', ')})`: ''}`);
                        if (alt5) segs.push(`5th - dating/pleasure${alt5Why.length? ` (${alt5Why.join(', ')})`: ''}`);
                        if (alt10) segs.push(`10th - authority/public${alt10Why.length? ` (${alt10Why.join(', ')})`: ''}`);
                        return (
                          <div className="text-xs">Context links: {segs.length ? segs.join(' | ') : '-'}</div>
                        );
                      })()}
                      <div className="text-xs mt-1">Dispositor path: {dispChain.length? dispChain.join(' -> ') : '-'} | mutual reception: {mutualReception? 'Yes':'No'} | light mediation: {translOrCollect}</div>
                      {(() => {
                        try {
                          const pMean = (name) => {
                            const dict = data?.planetary_meanings || {};
                            const entry = dict?.[name] || {};
                            const src = entry.crime || entry.general || '';
                            // take first 2 comma-separated snippets for brevity
                            const parts = String(src).split(',').map(s=> s.trim()).filter(Boolean);
                            return parts.slice(0,2).join('/');
                          };
                          const hMean = (h) => {
                            const dict = data?.house_meanings || {};
                            const entry = dict?.[String(h)] || {};
                            const src = entry.crime || entry.general || '';
                            const parts = String(src).split(',').map(s=> s.trim()).filter(Boolean);
                            return parts.slice(0,2).join('/');
                          };
                          const degKeys = (sign, degInt) => {
                            const dict = data?.degree_special || {};
                            const out = [];
                            const specials = dict?.special || {};
                            const key = `${sign}_${degInt}`;
                            if (specials[key] && specials[key].label) out.push(String(specials[key].label));
                            const sd = (dict?.sign_degrees || {})[sign];
                            if (Array.isArray(sd)) {
                              sd.forEach(entry => {
                                const arr = Array.isArray(entry?.degree) ? entry.degree : [];
                                if (arr.includes(degInt)) {
                                  const kws = Array.isArray(entry?.keywords) ? entry.keywords : [];
                                  if (kws.length) out.push(kws.slice(0,3).join('/'));
                                }
                              });
                            }
                            return out;
                          };
                          const chainDesc = dispChain.slice(0,4).map((nm) => {
                            const info = features?.planets?.[nm] || {};
                            const h = info?.house;
                            const sign = info?.sign;
                            let degInt = null;
                            if (typeof info?.degree_in_sign === 'number') degInt = Math.round(info.degree_in_sign);
                            else if (isFinite(info?.longitude)) degInt = Math.round(((Number(info.longitude)%30)+30)%30);
                            const bits = [];
                            const pk = pMean(nm); if (pk) bits.push(pk);
                            if (h != null) { const hk = hMean(h); if (hk) bits.push(hk); }
                            if (sign && degInt != null) {
                              const dk = degKeys(sign, degInt);
                              if (dk.length) bits.push(dk.join(' · '));
                            }
                            const pos = (sign && degInt != null) ? ` (${sign} ${degInt}°${h? ` · H${h}`:''})` : (h? ` (H${h})` : '');
                            return `${nm}${pos}: ${bits.join(' · ')}`;
                          });
                          return (
                            <div className="text-xs mt-1">
                              <div className="font-medium">Dispositor cues</div>
                              <ul className="list-disc ml-4">
                                {chainDesc.length ? chainDesc.map((t,i)=> <li key={i} className="text-[11px]">{t}</li>) : <li className="text-[11px]">-</li>}
                              </ul>
                            </div>
                          );
                        } catch(_) { return null; }
                      })()}
                      <div className="text-xs mt-1">Derived from the 7th: money H{derived.money.house}{derived.money.planets.length? ` -> ${derived.money.planets.join(', ')}`: ''} | home H{derived.home.house}{derived.home.planets.length? ` -> ${derived.home.planets.join(', ')}`: ''} | route/vehicle H{derived.comms.house}{derived.comms.planets.length? ` -> ${derived.comms.planets.join(', ')}`: ''} | friends H{derived.friends.house}{derived.friends.planets.length? ` -> ${derived.friends.planets.join(', ')}`: ''}</div>
                    </div>
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Behavioral Signals</div>
                      <ul className="text-xs list-disc ml-4 space-y-1">
                        <li>Mars contacts: {formatForensicAspectLabels(bpf.Mars)}</li>
                        <li>Saturn contacts: {formatForensicAspectLabels(bpf.Saturn)}</li>
                        <li>Neptune contacts: {formatForensicAspectLabels(bpf.Neptune)}</li>
                        <li>Pluto contacts: {formatForensicAspectLabels(bpf.Pluto)}</li>
                        <li>Sun/Moon fixed stars: {fsSunMoon.length? fsSunMoon.map(fsDescribe).filter(Boolean).join(' | '): '-'}</li>
                        <li>Cusp fixed stars: {fsCusps.length? fsCusps.map(fsDescribe).filter(Boolean).join(' | '): '-'}</li>
                      </ul>
                  {/* Dominance and Profile Hints */}
                  {(() => {
                    try {
                      const domPlanets = (data?.dominance && data.dominance.planets) ? data.dominance.planets : {};
                      const domArr = Object.entries(domPlanets).map(([name, v]) => ({ name, score: Number(v?.score)||0, level: String(v?.level||'') }));
                      domArr.sort((a,b)=> b.score - a.score);
                      const top2 = domArr.slice(0,2);
                      const profiles = data?.perpetrator_profiles || {};
                      let chosen = null;
                      for (const d of domArr) {
                        const key = `${d.name}_dominated`;
                        const pmatrix = profiles?.behavioral_trait_matrix || {};
                        const entry = (profiles && profiles[key]) || pmatrix?.[key];
                        if (entry) { chosen = { planet: d.name, entry }; break; }
                      }
                      const hints = [];
                      if (chosen && chosen.entry && typeof chosen.entry === 'object') {
                        const bc = chosen.entry.behavioral_characteristics;
                        if (bc && typeof bc === 'object') {
                          Object.values(bc).forEach(v=> { if (v && hints.length < 4) hints.push(String(v)); });
                        }
                        if (hints.length === 0) {
                          const mf = chosen.entry.manifestations;
                          if (mf && typeof mf === 'object') Object.values(mf).forEach(v=> { if (v && hints.length < 4) hints.push(String(v)); });
                        }
                        if (hints.length === 0) {
                          const ws = chosen.entry.warning_signs;
                          if (ws && typeof ws === 'object') Object.values(ws).forEach(v=> { if (v && hints.length < 4) hints.push(String(v)); });
                        }
                      }
                      return (
                        <div className="mt-2 pt-2 border-t border-zinc-200">
                          <div className="font-medium mb-1">Dominant signals</div>
                          <div className="text-xs mb-1">{top2.length ? top2.map(d=> `${d.name}: ${d.score} (${d.level})`).join(' · ') : '-'}</div>
                          {(() => {
                            // Brief one-line gloss for the top profiled planet
                            try {
                              if (!chosen) return null;
                              const bc = chosen.entry?.behavioral_characteristics || {};
                              const order = ['motive','method','temperament','public_behavior','profession'];
                              const parts = [];
                              for (const k of order) { if (bc && bc[k]) parts.push(String(bc[k])); }
                              const gloss = parts.slice(0,2).join(' · ');
                              return (
                                <div className="text-xs mb-1">Behavioral read: {chosen.planet} - {gloss || '-'}</div>
                              );
                            } catch(_) { return null; }
                          })()}
                          <div className="font-medium mb-1">Pattern hints{chosen ? ` (${chosen.planet})` : ''}</div>
                          <ul className="text-xs list-disc ml-4 space-y-1">
                            {hints.length ? hints.map((h,i)=> <li key={i}>{h}</li>) : <li>-</li>}
                          </ul>
                          {/* Relationship Signals */}
                          <div className="font-medium mt-2 mb-1">Relationship Signals</div>
                          {(() => {
                            try {
                              const sr = { Aries:'Mars', Taurus:'Venus', Gemini:'Mercury', Cancer:'Moon', Leo:'Sun', Virgo:'Mercury', Libra:'Venus', Scorpio:'Mars', Sagittarius:'Jupiter', Capricorn:'Saturn', Aquarius:'Saturn', Pisces:'Jupiter' };
                              const triplicity = {
                                Fire: { signs: ['Aries','Leo','Sagittarius'], rulers: ['Mars','Sun','Jupiter'] },
                                Earth: { signs: ['Taurus','Virgo','Capricorn'], rulers: ['Venus','Mercury','Saturn'] },
                                Air: { signs: ['Gemini','Libra','Aquarius'], rulers: ['Mercury','Venus','Saturn'] },
                                Water: { signs: ['Cancer','Scorpio','Pisces'], rulers: ['Moon','Mars','Jupiter'] },
                              };
                              const exaltation = { Sun:'Aries', Moon:'Taurus', Mercury:'Virgo', Venus:'Pisces', Mars:'Capricorn', Jupiter:'Cancer', Saturn:'Libra' };
                              const signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
                              const opp = (s) => signs[(signs.indexOf(s)+6)%12] || null;
                              const ascp = features?.planets?.[firstRuler] || {};
                              const dscp = features?.planets?.[seventhRuler] || {};
                              const victimSign = ascp?.sign; const perpSign = dscp?.sign;
                              const victimHouse = ascp?.house; const perpHouse = dscp?.house;
                              const planets = features?.planets || {};
                              const rulersMap = features?.house_rulers || {};
                              const recData = (data?.receptions) || {};
                              const mutual = Array.isArray(recData.mutual) ? recData.mutual : [];
                              const uni = Array.isArray(recData.top_unilateral) ? recData.top_unilateral : [];
                              const starRel = data?.relationship_star_hits || {};
                              const h7List = Object.entries(planets).filter(([,p])=> p?.house===7).map(([n])=> n);

                              // Level 1: Direct Rulership Connections (either direction)
                              const directVictRulesPerp = victimSign && sr[perpSign] === firstRuler;
                              const directPerpRulesVict = perpSign && sr[victimSign] === seventhRuler;
                              const level1 = { directVictRulesPerp, directPerpRulesVict };

                              // Level 2: Mutual Reception between first and seventh rulers
                              const isMutual = mutual.some(m => (m.p1===firstRuler && m.p2===seventhRuler) || (m.p1===seventhRuler && m.p2===firstRuler));

                              // Level 3: Triplicity shared
                              const triOf = (sign) => Object.keys(triplicity).find(k => triplicity[k].signs.includes(sign));
                              const level3 = victimSign && perpSign && (triOf(victimSign) === triOf(perpSign));

                              // Level 4: Exaltation/Fall relationships
                              const perpExaltSign = exaltation[seventhRuler];
                              const victExaltSign = exaltation[firstRuler];
                              const level4_victim_in_exalt_of_perp = victimSign && (victimSign === perpExaltSign);
                              const level4_victim_in_fall_of_perp = victimSign && (victimSign === opp(perpExaltSign));
                              const level4_perp_in_exalt_of_victim = perpSign && (perpSign === victExaltSign);
                              const level4_perp_in_fall_of_victim = perpSign && (perpSign === opp(victExaltSign));

                              // Level 5: Terms - check unilateral dignities containing 'term' in either direction
                              const termDir = uni.filter(u => ((u.receiving===firstRuler && u.received===seventhRuler) || (u.receiving===seventhRuler && u.received===firstRuler)) && (u.dignities||[]).includes('term'));
                              const level5_terms = termDir.length>0;

                              // House placement analysis
                              const houseFlags = [];
                              if (victimHouse===1) houseFlags.push('Victim ruler in 1st (self-contained)');
                              if (victimHouse===7) houseFlags.push('Victim ruler in 7th (in perpetrator domain)');
                              // Do not imply family involvement unless BOTH rulers share 4th or 10th; keep single flags neutral
                              if (victimHouse===4||victimHouse===10) houseFlags.push('Victim ruler in 4th/10th');
                              if (victimHouse===8) houseFlags.push('Victim ruler in 8th (shared resources/intimate)');
                              if (victimHouse===12) houseFlags.push('Victim ruler in 12th (hidden/secret)');
                              if (perpHouse===1) houseFlags.push('Perp ruler in 1st (immediate proximity)');
                              if (perpHouse===4||perpHouse===10) houseFlags.push('Perp ruler in 4th/10th');
                              if (perpHouse===6) houseFlags.push('Perp ruler in 6th (service/subordinate)');
                              if (perpHouse===11) houseFlags.push('Perp ruler in 11th (friend/associate)');
                              if (perpHouse===7) houseFlags.push('Perp ruler in 7th (in own domain)');
                              const sameHouse = (victimHouse!=null && perpHouse!=null && victimHouse===perpHouse);
                              if (sameHouse) houseFlags.push('Both rulers in same house (entanglement)');
                              // Critical combinations + scoring for crossovers
                              const crit = [];
                              {
                                const _vh = Number(victimHouse), _ph = Number(perpHouse);
                                if ((_vh===4 && _ph===4) || (_vh===10 && _ph===10)) crit.push('Both rulers in same family house (4 or 10)');
                              }
                              if (victimHouse===7 && perpHouse===1) crit.push('Victim in 7th + Perp in 1st (intimate partners)');
                              if ((victimHouse===1 && perpHouse===7) || (victimHouse===7 && perpHouse===1)) crit.push('1st/7th exchange (known to each other)');
                              // NOTE: scoring for house crossovers is applied after score is initialized below

                              // Traditional ruler analysis
                              const trad = [];
                              if (h7List.includes('Venus')) trad.push('Venus in 7th (female perpetrator possible)');
                              if (h7List.includes('Mars')) trad.push('Mars in 7th (male perpetrator possible)');
                              if ((planets?.Sun?.house===4) || (planets?.Sun?.angular && (rulersMap['4']==='Sun'))) trad.push('Sun/4th emphasis (father figure)');
                              if ((planets?.Moon?.house===10) || (planets?.Moon?.angular && (rulersMap['10']==='Moon'))) trad.push('Moon/10th emphasis (mother figure)');
                              if (Object.values(planets).some(p=> p?.house===5)) trad.push('5th house connection (child involvement)');
                              if (Object.values(planets).some(p=> p?.house===3)) trad.push('3rd house emphasis (sibling/neighbors)');

                              // Aspect analysis
                              const aspMap = features?.aspects || {};
                              const key1 = `${firstRuler}_to_${seventhRuler}`;
                              const key2 = `${seventhRuler}_to_${firstRuler}`;
                              const a = aspMap[key1] || aspMap[key2] || null;
                              const aspType = a?.type || null; // 'conjunction','trine','square','opposition','sextile'
                              const aspectFlags = [];
                              if (aspType) {
                                const easy = ['conjunction','trine','sextile'];
                                const hard = ['square','opposition'];
                                if (easy.includes(aspType)) aspectFlags.push(`Harmonious aspect (${aspType})`);
                                if (hard.includes(aspType)) aspectFlags.push(`Stressful aspect (${aspType})`);
                              } else {
                                aspectFlags.push('No direct aspects between rulers');
                              }

                              // Degree indicators
                              const degInt = (nm)=> { const d = planets?.[nm]?.degree_in_sign; return (typeof d==='number')? Math.round(d): null; };
                              const dVict = degInt(firstRuler);
                              const dPerp = degInt(seventhRuler);
                              const degFlags = [];
                              const mark = (lab,cond)=> { if (cond) degFlags.push(lab); };
                              mark('0° new situation (victim)', dVict===0);
                              mark('0° new situation (perp)', dPerp===0);
                              mark('15° assassination degree (victim)', dVict===15);
                              mark('15° assassination degree (perp)', dPerp===15);
                              mark('29° crisis (victim)', dVict===29);
                              mark('29° crisis (perp)', dPerp===29);
                              // Fixed stars on significators
                              const relStars = starRel || {};
                              const starNames = (arr)=> (Array.isArray(arr)? arr.map(h=> h?.name).filter(Boolean): []);
                              const starFlags = [];
                              const ascStars = starNames(relStars.asc_ruler);
                              const dscStars = starNames(relStars.dsc_ruler);
                              if (ascStars.length) starFlags.push(`ASC ruler on ${ascStars.join('/')}`);
                              if (dscStars.length) starFlags.push(`DSC ruler on ${dscStars.join('/')}`);

                              // Scoring
                              let score = 0; const reasons = [];
                              // House crossover scoring (applied first)
                              if (victimHouse===7) { score+=2; reasons.push('Victim ruler in 7th (+2)'); }
                              if (perpHouse===1) { score+=2; reasons.push('Perp ruler in 1st (+2)'); }
                              if (perpHouse===7) { score+=1; reasons.push('Perp ruler in 7th (+1)'); }
                              if (sameHouse) { score+=2; reasons.push('Both rulers in same house (+2)'); }
                              { const angSet = new Set([1,4,7,10]); if (angSet.has(Number(victimHouse)) && angSet.has(Number(perpHouse))) { score+=1; reasons.push('Both rulers angular (+1)'); } }
                              if (level1.directVictRulesPerp) { score+=3; reasons.push('Victim ruler rules perpetrator sign'); }
                              if (level1.directPerpRulesVict) { score+=3; reasons.push('Perp ruler rules victim sign'); }
                              if (isMutual) { score+=4; reasons.push('Mutual reception'); }
                              if (level3) { score+=2; reasons.push('Shared triplicity'); }
                              if (level4_victim_in_exalt_of_perp) { score+=2; reasons.push('Victim in exaltation of perpetrator'); }
                              if (level4_perp_in_exalt_of_victim) { score+=2; reasons.push('Perp in exaltation of victim'); }
                              if (level4_victim_in_fall_of_perp) { score+=1; reasons.push('Victim in fall of perpetrator'); }
                              if (level4_perp_in_fall_of_victim) { score+=1; reasons.push('Perp in fall of victim'); }
                              if (level5_terms) { score+=1; reasons.push('Terms/bounds connection'); }
                              if (crit.length) { score+=2; reasons.push('Critical house combination'); }
                              if (trad.some(t=> t.includes('7th'))) { score+=1; reasons.push('7th-house traditional indicator'); }
                              if (aspType){ const easy=['conjunction','trine','sextile']; const hard=['square','opposition']; if (easy.includes(aspType)) { score+=2; reasons.push('Harmonious aspect'); } else if (hard.includes(aspType)) { score+=1; reasons.push('Stressful aspect (known)'); } }
                              if (dVict===0||dVict===15||dVict===29||dPerp===0||dPerp===15||dPerp===29) { score+=1; reasons.push('Critical degree'); }
                              const violentStars = new Set(['Algol','Antares']);
                              const protectStars = new Set(['Spica']);
                              const hasViolent = [...ascStars, ...dscStars].some(n=> violentStars.has(n));
                              const hasProtect = [...ascStars, ...dscStars].some(n=> protectStars.has(n));
                              if (hasViolent) { score+=2; reasons.push('Violent fixed star on significator'); }
                              if (hasProtect) { score+=1; reasons.push('Protective fixed star on significator'); }

                              const relationshipSummary = summarizeForensicRelationshipLink({
                                score,
                                victimHouse,
                                perpHouse,
                                seventhHousePlanets: h7List,
                                isMutual,
                                forensicResult: data,
                              });
                              const bothIn4 = Number(victimHouse) === 4 && Number(perpHouse) === 4;
                              const bothIn10 = Number(victimHouse) === 10 && Number(perpHouse) === 10;
                              const relationshipRows = buildRelationshipDisplayRows({
                                firstRuler,
                                moonContacts: aspectTo('Moon'),
                                ascRulerContacts: aspectTo(firstRuler),
                                directVictRulesPerp: level1.directVictRulesPerp,
                                directPerpRulesVict: level1.directPerpRulesVict,
                                isMutual,
                                level3,
                                exaltationFallFlags: [
                                  level4_victim_in_exalt_of_perp ? 'victim in exaltation of perpetrator' : null,
                                  level4_perp_in_exalt_of_victim ? 'perpetrator in exaltation of victim' : null,
                                  level4_victim_in_fall_of_perp ? 'victim in fall of perpetrator' : null,
                                  level4_perp_in_fall_of_victim ? 'perpetrator in fall of victim' : null,
                                ].filter(Boolean),
                                level5Terms: level5_terms,
                                houseConnections: (bothIn4 || bothIn10)
                                  ? ['shared family-house placement (4th/10th)']
                                  : houseFlags.concat(crit),
                                traditionalCues: trad,
                                aspectTies: aspectFlags,
                                degreeStarCues: degFlags.concat(starFlags),
                                score,
                                relationshipType: relationshipSummary.relationshipType,
                                confidence: relationshipSummary.confidence,
                              });

                              return (
                                <div className="text-xs space-y-1">
                                  <div>Contact signals: {relationshipRows.contactSignals}</div>
                                  <div>Rulership links: {relationshipRows.rulershipLinks}</div>
                                  <div>Mutual reception: {relationshipRows.mutualReception}</div>
                                  <div>Shared triplicity: {relationshipRows.sharedTriplicity}</div>
                                  <div>Exaltation/fall ties: {relationshipRows.exaltationFallTies}</div>
                                  <div>Term/bounds ties: {relationshipRows.termBoundsTies}</div>
                                  <div>House overlap: {relationshipRows.houseOverlap}</div>
                                  <div>Traditional cues: {relationshipRows.traditionalCues}</div>
                                  <div>Aspect ties: {relationshipRows.aspectTies}</div>
                                  <div>Degree/star cues: {relationshipRows.degreeStarCues}</div>
                                  <div className="font-medium mt-1">Connection summary: {relationshipRows.connectionSummary}</div>
                                </div>
                              );
                            } catch(_) { return <div className="text-xs">-</div>; }
                          })()}
                        </div>
                      );
                    } catch(_) { return null; }
                  })()}
                    </div>
                  </div>
                );
              })()}
            </div>
          )
        ))}

        {card('Witness & Accomplice Detection', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {(() => {
                const pls = features?.planets || {};
                const houseList = (h)=> Object.entries(pls).filter(([,p])=> p?.house===h).map(([n])=> n);
                const mercuryHouse = pls?.Mercury?.house || '-';
                const witnesses = ['Mercury', ...houseList(3)];
                const associates = houseList(11);
                const hidden = [...houseList(6), ...houseList(12)];
                const groupings = Object.values(pls).reduce((acc,p)=>{ const h=p?.house; if (!h) return acc; acc[h]=(acc[h]||0)+1; return acc; }, {});
                const multiHouses = Object.entries(groupings).filter(([,c])=> c>=2).map(([h])=> h);
                const wdict = data?.witness_accomplice || {};
                const mod = (k)=> (wdict?.condition_modifiers?.[k] || '');
                const solar = features?.solar || {};
                const inSolar = (k, p) => Array.isArray(solar?.[k]) && solar[k].includes(p);
                const houseGroup = (h) => { const n=Number(h); if ([1,4,7,10].includes(n)) return 'angular'; if ([2,5,8,11].includes(n)) return 'succedent'; return 'cadent'; };
                const planetQualifiers = (name) => {
                  try {
                    const p = pls?.[name] || {};
                    if (!p || p.house==null) return [];
                    const tags = [];
                    tags.push(mod(houseGroup(p.house)));
                    if (p.retrograde) tags.push(mod('retrograde'));
                    if (p.anaretic) tags.push(mod('anaretic'));
                    if (p.ingress) tags.push(mod('ingress'));
                    if (p.via_combusta) tags.push(mod('via_combusta'));
                    if (inSolar('cazimi', name)) tags.push(mod('cazimi'));
                    if (inSolar('combustion', name)) tags.push(mod('combustion'));
                    if (inSolar('under_beams', name)) tags.push(mod('under_beams'));
                    return tags.filter(Boolean).slice(0,3);
                  } catch(_) { return []; }
                };
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Additional Entities</div>
                      <ul className="text-xs list-disc ml-4 space-y-1">
                        <li>Mercury (witness/sibling): H{mercuryHouse}{(() => { const q=planetQualifiers('Mercury'); return q.length? ` - ${q.join(' · ')}` : ''; })()}</li>
                        <li>3rd House (neighbors/local): {(() => { const arr = houseList(3); const out = arr.map(p=> { const q=planetQualifiers(p); return q.length? `${p} - ${q.join(' · ')}`: p; }); return out.length? out.join(', '): '-'; })()}</li>
                        <li>11th House (friends/associates): {(() => { const out = associates.map(p=> { const q=planetQualifiers(p); return q.length? `${p} - ${q.join(' · ')}`: p; }); return out.length? out.join(', '): '-'; })()}</li>
                        <li>6th/12th (hidden enemies): {(() => { const out = hidden.map(p=> { const q=planetQualifiers(p); return q.length? `${p} - ${q.join(' · ')}`: p; }); return out.length? out.join(', '): '-'; })()}</li>
                        <li>Planetary groupings (≥2 in house): {multiHouses.length? multiHouses.map(h=> `H${h}`).join(', '): '-'}</li>
                      </ul>
                    </div>
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Witness List</div>
                      <div className="text-xs">{witnesses.join(', ') || '-'}</div>
                      {(() => {
                        try {
                          const base = wdict?.roles?.Mercury?.base;
                          const q = planetQualifiers('Mercury');
                          if (!base && q.length===0) return null;
                          return (
                            <div className="text-[11px] text-zinc-600 mt-1">Mercury: {(base||'').trim()}{q.length? ` - ${q.join(' · ')}`:''}</div>
                          );
                        } catch(_) { return null; }
                      })()}
                    </div>
                  </div>
                );
              })()}
            </div>
          )
        ))}

        {card('Deception Configuration', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm">
              {(() => {
                try {
                  const pls = features?.planets || {};
                  const asp = features?.aspects || {};
                  const houses = features?.houses || {};
                  const solar = features?.solar || {};
                  const getA = (a,b,types)=> {
                    const tset = types? new Set(types.map(x=> String(x).toLowerCase())): null;
                    const hit = (k)=> {
                      const v = asp[k]; if (!v) return false;
                      if (tset && !tset.has(String(v.type||'').toLowerCase())) return false;
                      return true;
                    };
                    return hit(`${a}_to_${b}`) || hit(`${b}_to_${a}`);
                  };
                  const hasApp = (a,b)=> {
                    const va = asp[`${a}_to_${b}`]; const vb = asp[`${b}_to_${a}`];
                    return (va && va.applying===true) || (vb && vb.applying===true);
                  };
                  const inHouse = (p,h)=> (pls?.[p]?.house === h);
                  const hard = ['square','opposition'];
                  let score = 0;
                  const flags = [];
                  // Mercury-based
                  if (getA('Mercury','Neptune')) { score += hasApp('Mercury','Neptune')? 2:1; flags.push('Mercury–Neptune'); }
                  if (pls?.Mercury?.retrograde) { score += 1; flags.push('Mercury retrograde'); }
                  if (Array.isArray(solar?.combustion) && solar.combustion.includes('Mercury')) { score += 1; flags.push('Mercury combust'); }
                  if (inHouse('Mercury',12)) { score += 1; flags.push('Mercury in 12th'); }
                  if (pls?.Mercury?.mute_sign) { score += 1; flags.push('Mercury in mute sign'); }
                  // Neptune: master deceiver
                  const personals = ['Sun','Moon','Mercury','Venus','Mars'];
                  if (personals.some(p=> getA('Neptune', p))) { score += 1; flags.push('Neptune to personals'); }
                  if (inHouse('Neptune',7)) { score += 1; flags.push('Neptune in 7th'); }
                  if (inHouse('Neptune',12)) { score += 1; flags.push('Neptune in 12th'); }
                  if (houses?.neptune_angular === true) { score += 1; flags.push('Neptune angular'); }
                  // Mars–Neptune
                  if (getA('Mars','Neptune',['opposition'])) { score += 2; flags.push('Mars–Neptune opposition'); }
                  if (getA('Mars','Neptune',['square'])) { score += 1; flags.push('Mars–Neptune square'); }
                  // Venus–Saturn
                  if (getA('Venus','Saturn',hard)) { score += 1; flags.push('Venus–Saturn hard'); }
                  const vSign = pls?.Venus?.sign;
                  if (['Aries','Scorpio'].includes(vSign) && (getA('Venus','Saturn') || pls?.Saturn?.angular)) { score += 1; flags.push('Venus detriment w/ Saturn'); }
                  // House-based
                  if (houses?.emphasis12_strong) { score += 1; flags.push('12th house emphasis'); }
                  if (houses?.seventh_ruler_in_12th) { score += 1; flags.push('7th ruler in 12th'); }
                  if (pls?.Sun?.house===12 || pls?.Moon?.house===12) { score += 1; flags.push('Sun/Moon in 12th'); }
                  if (houses?.mute_signs_on_angles) { score += 1; flags.push('Mute signs on angles'); }
                  if (houses?.mute_sign_on_3rd_or_9th) { score += 1; flags.push('Mute signs on 3rd/9th'); }
                  if (houses?.north_node_in_8th) { score += 1; flags.push('North Node in 8th'); }
                  // NN in 4th - domestic deception tilt
                  const nnHouse = houses?.north_node_house;
                  if (nnHouse === 4) { score += 1; flags.push('North Node in 4th'); }
                  // Saturn–Neptune cover-up
                  if (getA('Saturn','Neptune')) { score += 1; flags.push('Saturn–Neptune'); }
                  // Node + deceptive planets
                  const nodeNames = ['North Node','Node'];
                  if (nodeNames.some(nm => getA(nm,'Neptune'))) { score += 1; flags.push('Node+Neptune'); }
                  if (nodeNames.some(nm => getA(nm,'Mercury'))) { score += 1; flags.push('Node+Mercury'); }

                  // Truth indicators (streamlined)
                  let truth = 0; const truths = [];
                  if (!houses?.mute_signs_on_angles && !houses?.mute_sign_on_3rd_or_9th) { truth += 1; truths.push('No mute sign emphasis'); }

                  const adjusted = Math.max(0, score - truth);
                  const level = (s)=> s>=8? 'Critical' : (s>=5? 'High' : (s>=3? 'Medium' : 'Low'));
                  const lvl = level(adjusted);
                  const show = flags.slice(0,8);
                  const flagKeywords = {
                    'Mercury–Neptune': 'Lies/cover‑ups; confusion and disinfo',
                    'Mercury retrograde': 'Revisions, reversals, withheld info',
                    'Mercury combust': 'Hidden facts; impaired communication',
                    'Mercury in 12th': 'Secrets; behind‑the‑scenes messaging',
                    'Mercury in mute sign': 'Silence; refusal to speak plainly',
                    'Neptune to personals': 'Illusion/fantasy around key actors',
                    'Neptune in 7th': 'Partner/open enemy deception',
                    'Neptune in 12th': 'Hidden deception; secret enemies',
                    'Neptune angular': 'Major staged/disguised events',
                    'Mars–Neptune opposition': 'Abduction/kidnapping cover',
                    'Mars–Neptune square': 'Violence + deception; missing evidence',
                    'Venus–Saturn hard': 'Relational deception/abuse',
                    'Venus detriment w/ Saturn': 'Deceptive charm; relational harm',
                    '12th house emphasis': 'Hidden enemies; cover‑ups; confinement',
                    '7th ruler in 12th': 'Partner’s secrecy',
                    'Sun/Moon in 12th': 'Identity hidden; secret activities',
                    'Mute signs on angles': 'Secrecy around the chart axis',
                    'Mute signs on 3rd/9th': 'Deception in comms/legal',
                    'North Node in 8th': 'Schemes/insurance ruses',
                    'North Node in 4th': 'Domestic staging/real estate ruse',
                    'Saturn–Neptune': 'Authority/institutional cover‑up',
                    'Node+Neptune': 'Karmic ruse with Neptune',
                    'Node+Mercury': 'Karmic ruse in communications',
                    'Jupiter↔Mercury easy': 'Clarity, lawful/ethical comms',
                    'Strong 3rd/9th': 'Robust comms/legal axis',
                    'No mute sign emphasis': 'Open, explicit signaling',
                    'Direct motion predominance': 'Less revision/reversal tendency',
                  };
                  const keywordLines = [];
                  flags.forEach(f=> { const k = flagKeywords[f]; if (k) keywordLines.push(`• ${f} - ${k}`); });
                  truths.forEach(f=> { const k = flagKeywords[f]; if (k) keywordLines.push(`• ${f} - ${k}`); });
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="border rounded p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="font-medium">Score & Level</div>
                          {(() => {
                            const col = (lvl==='Critical')? '#DC2626' : (lvl==='High')? '#F97316' : (lvl==='Medium')? '#F59E0B' : '#10B981';
                            const hatch = `repeating-linear-gradient(45deg, ${col} 0, ${col} 2px, rgba(255,255,255,0.25) 2px, rgba(255,255,255,0.25) 4px)`;
                            const active = (lvl==='Critical')?4:(lvl==='High')?3:(lvl==='Medium')?2:1;
                            return (
                              <div className="flex gap-[2px]" aria-hidden="true">
                                {Array.from({ length: 4 }).map((_, i) => (
                                  <div key={i} className="w-4 h-3 rounded-[2px] border border-zinc-300"
                                       style={ i < active ? { backgroundImage: hatch, backgroundColor: col, boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.06)' } : {} } />
                                ))}
                              </div>
                            );
                          })()}
                        </div>
                        <div className="text-xs">Deception score: <span className="font-semibold">{adjusted}</span> - <span className="font-semibold">{lvl}</span> <span className="text-[10px] text-zinc-500">(raw {score}{truth? ` − ${truth} truth`: ''})</span></div>
                        <div className="text-[11px] text-zinc-600">Higher scores = more indicators for staged/hidden narratives.</div>
                      </div>
                      <div className="border rounded p-2">
                        <div className="font-medium mb-1">Key Indicators</div>
                        <div className="text-xs">{show.length? show.join(' · ') : '-'}</div>
                      </div>
                      <div className="border rounded p-2 md:col-span-2">
                        <div className="font-medium mb-1">Indicator Keywords</div>
                        <div className="text-[11px] whitespace-pre-line">{keywordLines.length? keywordLines.join('\n') : '-'}</div>
                      </div>
                    </div>
                  );
                } catch(_) {
                  return <div className="text-xs text-zinc-500">Unavailable</div>;
                }
              })()}
            </div>
          )
        ))}

        {card('Final outcome determination', (
          loading ? <div className="text-sm text-zinc-500">Loading…</div> : (
            <div className="text-sm space-y-3">
              {(() => {
                const cusps = features?.house_cusps || [];
                const cusp4 = Number(cusps?.[3]);
                const icDeg = isFinite(cusp4) ? degreeTextFromLon(cusp4) : '-';
                const cusp4Sign = isFinite(cusp4) ? signFromLon(cusp4) : '-';
                const icDict = data?.ic_sign_meanings || {};
                const icExpl = cusp4Sign && icDict?.[cusp4Sign]?.outcome;
                const ruler4 = features?.house_rulers?.['4'] || features?.house_rulers?.[4] || null;
                const ruler4House = ruler4 ? features?.planets?.[ruler4]?.house : null;
                const icRulerDict = data?.ic_ruler_house_meanings || {};
                const icRulerExpl = (ruler4House != null) ? (icRulerDict?.[String(ruler4House)]?.outcome) : null;
                const planets = features?.planets || {};
                const in4All = Object.entries(planets).filter(([,p])=> p?.house===4).map(([n])=> n);
                const icP4 = data?.ic_planet_in_4th || {};
                const nodeNames = new Set(['North Node','South Node','Node']);
                const nodesIn4 = in4All.filter(nm => nodeNames.has(nm));
                const in4 = in4All.filter(nm => !nodeNames.has(nm));
                const in4Expl = (() => {
                  try {
                    if (!Array.isArray(in4) || in4.length===0) return [];
                    return in4.map(nm => {
                      const expl = icP4?.[nm];
                      return expl ? `${nm} - ${expl}` : nm;
                    });
                  } catch(_) { return in4; }
                })();
                const nodeModExpl = (() => {
                  try {
                    if (!nodesIn4.length) return null;
                    // Prefer explicit North/South Node descriptions, else generic Nodes concept
                    const parts = nodesIn4.map(nm => icP4?.[nm] || 'Karmic hinge; intensifies/tilts the ending');
                    const uniq = Array.from(new Set(parts));
                    return `Node modifier: ${uniq.join(' · ')}`;
                  } catch(_) { return null; }
                })();
                const benefics = ['Venus','Jupiter'];
                const malefics = ['Mars','Saturn'];
                const ben4 = in4.filter(n=> benefics.includes(n));
                const mal4 = in4.filter(n=> malefics.includes(n));
                const outcomeTags = [
                  { label: 'Benefics in 4th -> Positive resolution/recovery', ok: ben4.length>0, extra: ben4.join(', ') },
                  { label: 'Malefics in 4th -> Tragic/violent conclusion', ok: mal4.length>0, extra: mal4.join(', ') },
                  { label: 'Empty 4th House -> Inconclusive/ongoing case', ok: in4.length===0, extra: '' },
                  { label: 'Multiple planets in 4th -> Complex resolution', ok: in4.length>=2, extra: in4.length>=2 ? in4.join(', ') : '' },
                ];
                const asp = features?.aspects || {};
                const infl = (() => {
                  try {
                    const classical = new Set(['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn']);
                    const out = [];
                    for (const [k, v] of Object.entries(asp)) {
                      if (!v) continue;
                      const [p1, p2] = k.split('_to_');
                      const involves4 = (ruler4 && (p1===ruler4 || p2===ruler4)) || in4.includes(p1) || in4.includes(p2);
                      if (!involves4) continue;
                      // Show applying influences from classical planets; hide Node‑only hits for clarity
                      if (v.applying !== true) continue;
                      const other = in4.includes(p1) || (ruler4 && p1===ruler4) ? p2 : p1;
                      if (!classical.has(other)) continue;
                      out.push({ p1, p2, v });
                    }
                    out.sort((a,b)=> {
                      const ao = Math.abs(Number(a.v?.orb ?? 999));
                      const bo = Math.abs(Number(b.v?.orb ?? 999));
                      return ao - bo;
                    });
                    return out.slice(0,5).map(({p1,p2,v})=> `${p1} ${v.type || ''} ${p2}${v.applying? ' (app)':''}`);
                  } catch(_) { return []; }
                })();
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Primary Analysis Points</div>
                      <ul className="text-xs list-disc ml-4 space-y-1">
                        <li>4th House Cusp Sign {'->'} {cusp4Sign}{icExpl? ` - ${icExpl}`: ''}</li>
                        <li>4th House Ruler Placement {'->'} {ruler4 ? `${ruler4} in H${ruler4House ?? '-'}` : '-'}{icRulerExpl? ` - ${icRulerExpl}`: ''}</li>
                        <li>Planets in 4th House {'->'} {in4Expl.length? in4Expl.join(' · ') : '-'}{nodeModExpl? ` · ${nodeModExpl}`:''}</li>
                        <li>IC (Nadir) Degree {'->'} {icDeg}</li>
                        <li>Aspects influencing 4th House (ruler/occupants) {'->'} {infl.length? infl.join(' · ') : '-'}</li>
                      </ul>
                    </div>
                    <div className="border rounded p-2">
                      <div className="font-medium mb-1">Outcome Classification Matrix</div>
                      <div className="space-y-1">
                        {outcomeTags.map((t, i)=> (
                          <div key={i} className={`text-xs px-2 py-1 rounded border ${t.ok? 'border-emerald-300 bg-emerald-50' : 'border-zinc-200'}`}>
                            {t.label}{t.extra? ` - ${t.extra}`:''}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )
        ))}
      </div>
    </div>
  );
}

// Subcomponents per spec

function ArabicLotsPanel({ data }){
  const lots = data?.arabic_parts || {};
  const [deathVar, setDeathVar] = useState('A'); // 'A'|'B'
  const [poisonVar, setPoisonVar] = useState('V1'); // 'V1'|'V2'
  const [planeVar, setPlaneVar] = useState('V1'); // 'V1'|'V2'
  const [showOptions, setShowOptions] = useState(false);
  const rows = [];
  const push = (key, label) => { const x = lots[key]; if (x) rows.push({ label, x }); };
  push('fortune', 'Fortune');
  push('spirit', 'Spirit');
  push('peril', 'Peril');
  push(deathVar==='A'?'deathA':'deathB', `Death ${deathVar}`);
  push(poisonVar==='V1'?'poison_v1':'poison_v2', `Poison ${poisonVar}`);
  push(planeVar==='V1'?'plane_v1':'plane_v2', `Plane ${planeVar}`);
  return (
    <div className="text-sm h-full flex flex-col">
      {/* In-tile vertical expander with arrow on LEFT */}
      <div className="mb-2">
        <button
          type="button"
          onClick={()=> setShowOptions(v=>!v)}
          className="w-full text-left flex items-center gap-2 text-[11px] text-zinc-700 hover:text-zinc-900"
        >
          <span className="inline-block w-4">{showOptions ? '▾' : '▸'}</span>
          <span>Formula Options</span>
        </button>
        {showOptions && (
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px]">
            <div className="flex items-center gap-1">
              <span>Death</span>
              <button onClick={()=>setDeathVar('A')} className={`px-1.5 py-0.5 rounded border ${deathVar==='A'?'border-zinc-800':'border-zinc-300'}`}>A</button>
              <button onClick={()=>setDeathVar('B')} className={`px-1.5 py-0.5 rounded border ${deathVar==='B'?'border-zinc-800':'border-zinc-300'}`}>B</button>
            </div>
            <div className="flex items-center gap-1">
              <span>Poison</span>
              <button onClick={()=>setPoisonVar('V1')} className={`px-1.5 py-0.5 rounded border ${poisonVar==='V1'?'border-zinc-800':'border-zinc-300'}`}>V1</button>
              <button onClick={()=>setPoisonVar('V2')} className={`px-1.5 py-0.5 rounded border ${poisonVar==='V2'?'border-zinc-800':'border-zinc-300'}`}>V2</button>
            </div>
            <div className="flex items-center gap-1">
              <span>Plane</span>
              <button onClick={()=>setPlaneVar('V1')} className={`px-1.5 py-0.5 rounded border ${planeVar==='V1'?'border-zinc-800':'border-zinc-300'}`}>V1</button>
              <button onClick={()=>setPlaneVar('V2')} className={`px-1.5 py-0.5 rounded border ${planeVar==='V2'?'border-zinc-800':'border-zinc-300'}`}>V2</button>
            </div>
          </div>
        )}
      </div>
      <div className="astro-scroll-shell flex-1">
        <div className="astro-scroll space-y-2">
          {rows.length===0 ? (
            <div className="text-zinc-500">No lots</div>
          ) : rows.map((r, idx)=> (
            <div key={idx}>
              <div className="flex justify-between">
                <span className="font-medium">{r.label}</span>
                <span className="text-zinc-600">{degreeTextFromLon(r.x.lon)} {signFromLon(r.x.lon)}</span>
              </div>
              <div className="text-xs text-zinc-600">H{r.x.house ?? '-'} · Ruler: {r.x.ruler}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SectPanel({ data }) {
  const sect = data?.sect;
  if (!sect) {
    return <div className="text-sm text-zinc-500">No sect data</div>;
  }
  const chipsCls = 'text-xs rounded-full border border-zinc-200 bg-white px-2 py-1';
  const nice = (x)=> (x==null||x===undefined? '-' : String(x));
  const isDay = sect.chart_sect === 'diurnal';
  const chartLabel = isDay ? 'Day' : 'Night';
  const mercuryLabel = (()=>{
    if (!sect.mercury_phase) return 'Mercury - -';
    const asg = sect.mercury_assigned_sect === 'diurnal' ? 'day sect' : sect.mercury_assigned_sect === 'nocturnal' ? 'night sect' : '-';
    return `Mercury - ${sect.mercury_phase} star (${asg})`;
  })();
  const rows = (sect.planets||[]).filter(p=> p && p.planet).map(p=> ({
    name: p.planet,
    inSect: p.in_sect === true,
    hayz: !!p.hayz,
    polMatch: p.sign_polarity_match === true,
    hemMatch: p.hemisphere_match === true,
  }));
  return (
    <div className="flex flex-col">
      <div className="space-x-2 space-y-2 flex flex-wrap items-center mb-2">
        <span className={chipsCls}>{chartLabel} · Sect light {PlanetSymbols[sect.sect_light] || sect.sect_light}</span>
        <span className={chipsCls}>Malefic of sect {PlanetSymbols[sect.malefic_of_sect] || sect.malefic_of_sect}</span>
        <span className={chipsCls}>Benefic of sect {PlanetSymbols[sect.benefic_of_sect] || sect.benefic_of_sect}</span>
        <span className={chipsCls}>{mercuryLabel}</span>
      </div>
      {/* explanatory text removed per request */}
      <div>
        {rows.length === 0 ? (
          <div className="text-sm text-zinc-500">No planets listed</div>
        ) : (
          <div className="space-y-1">
            {rows.map((r, i)=> (
              <div key={i} className="flex items-center justify-between border-b border-zinc-100 py-1 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-lg leading-none">{PlanetSymbols[r.name] || '·'}</span>
                  <span className="font-medium">{r.name}</span>
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  <span className={`px-1.5 py-0.5 rounded border ${r.inSect? 'border-emerald-300 text-emerald-700':'border-rose-300 text-rose-700'}`}>{r.inSect? 'in-sect':'out-of-sect'}</span>
                  {r.hayz && <span className="px-1.5 py-0.5 rounded border border-blue-300 text-blue-700">hayz</span>}
                  {r.polMatch && <span className="px-1.5 py-0.5 rounded border border-zinc-300">polarity</span>}
                  {r.hemMatch && <span className="px-1.5 py-0.5 rounded border border-zinc-300">hemisphere</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="mt-auto text-[11px] text-zinc-500">Malefic moderated by sect: {isDay? 'Saturn':'Mars'}.</div>
    </div>
  );
}



function ChartMock({ hours, data, includeModern, onToggleModern, onRefresh, onLocationChange, onSnap, snapDisabled, mode, manualIso, onForensic, showForensicButton=true, onCasePrompt, houseSystem, onHouseSystemChange }){
  // House system selector options (Swiss codes)
  const HOUSE_OPTIONS = [
    { code: 'R', label: 'Regiomontanus' },
    { code: 'P', label: 'Placidus' },
    { code: 'E', label: 'Equal' },
    { code: 'W', label: 'Whole Sign' },
    { code: 'O', label: 'Porphyry' },
    { code: 'C', label: 'Campanus' },
    { code: 'K', label: 'Koch' },
    { code: 'T', label: 'Topocentric' },
  ];
  const [now, setNow] = useState(new Date());
  // Only tick in realtime; freeze at manual time when in manual mode
  useEffect(()=>{
    if (mode === 'manual') return; // no ticking; show system time only in realtime
    const t = setInterval(()=> setNow(new Date()), 30000);
    return ()=> clearInterval(t);
  }, [mode]);
  const clockDt = useMemo(() => {
    if (mode === 'manual' && manualIso) {
      try { return new Date(manualIso); } catch { /* ignore */ }
    }
    return now;
  }, [mode, manualIso, now]);
  const mins = clockDt.getHours()*60 + clockDt.getMinutes();
  const angle = (mins/1440)*360;
  const planetGlyphs = { Sun:'☉', Moon:'☽', Mercury:'☿', Venus:'♀', Mars:'♂', Jupiter:'♃', Saturn:'♄', Uranus:'♅', Neptune:'♆', Pluto:'♇', 'North Node':'☊' };
  const asc = (data?.house_cusps && data.house_cusps.length>0) ? Number(data.house_cusps[0]) : 0;
  const cusps = (data?.house_cusps && data.house_cusps.length===12) ? data.house_cusps : undefined;
  const planets = (data?.planets||[])
    .filter(p => p && typeof p === 'object' && p.planet && (p.longitude!=null))
    .map(p=>({ id: p.planet, glyph: planetGlyphs[p.planet] || '·', lon: Number(p.longitude)||0, retro: !!p.retrograde, house: p.house, label: p.planet }));
  const [editingLoc, setEditingLoc] = useState(false);
  const [locInput, setLocInput] = useState('');
  const chartLocationLabel = data?.location || 'Set location';
  const displayedTimezoneLabel = formatAstroClockTimezoneLabel({
    timestamp: data?.timestamp,
    timezone: data?.timezone,
    timezoneLabel: data?.timezone_label,
  });
  const defaultCasePrompt = async () => {
    try {
      let name = '';
      try { name = (window.prompt && window.prompt('Enter Case Name')) || ''; } catch(_) { name = ''; }
      if (!name) name = 'Enter case name here';
      const txt = `Case name: ${name}\n\nTask:\nProvide the timestamp + location/time-zone package needed to cast forensic-astrology event charts. Do not generate charts or interpretations-only deliver items (1) and (2) below. Make best-judgment choices and state assumptions briefly (no follow-up questions).\n\n1) Identify Event Timestamps\n   - Primary: the earliest reliable discovery/notification moment.\n   - Alternates: (a) emergency/official log time, (b) legal pronouncement (e.g., time of death), (c) last confirmed alive/seen.\n   - For each timestamp: give local time (to the minute), UTC equivalent, a short reliability note, and 1–2 source links. If sources conflict, pick the most authoritative, explain why, and list the runner-up time(s).\n\n2) Locations & Time Zones\n   - For each timestamp: provide the full street address (venue + city + country), precise coordinates in decimal degrees (lat/long), time-zone name and UTC offset, and whether daylight saving time was in effect at that moment. Show the UTC conversion you used.\n\nOutput format (one markdown table):\nLabel | Local Time | UTC | Address | Lat/Long | Time Zone (incl. DST) | Source(s) | Reliability Notes`;
      await safeCopyText(txt);
    } catch (_) {}
  };
  return (
    <div className={`${panelCls} relative`}>
      <div className="mb-3 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-zinc-600 hidden sm:inline">Modern</span>
            <label className="relative inline-flex items-center cursor-pointer select-none">
              <input
                type="checkbox"
                className="sr-only peer"
                checked={!!includeModern}
                onChange={onToggleModern}
              />
              <div className="w-10 h-5 bg-zinc-300 peer-checked:bg-zinc-800 rounded-full transition-colors"></div>
              <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
              <span className="ml-2 text-[11px]">♅ ♆ ♇</span>
            </label>
          </div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-sm">Chart</h3>
            {displayedTimezoneLabel && (
              <span className="px-2 py-0.5 rounded-full border border-zinc-300 bg-white/80 text-[11px] text-zinc-600">
                {displayedTimezoneLabel}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-zinc-600">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <label className="hidden md:inline text-zinc-600">Houses</label>
            <select
              className="px-2 py-0.5 rounded border border-zinc-300 bg-white/80"
              value={houseSystem || 'R'}
              onChange={(e)=> onHouseSystemChange && onHouseSystemChange(e.target.value)}
              title="House system"
            >
              {HOUSE_OPTIONS.map(opt => (
                <option key={opt.code} value={opt.code}>{opt.label}</option>
              ))}
            </select>
            <span className="max-w-[220px] truncate rounded-full border border-zinc-200 bg-zinc-50/80 px-2 py-0.5 text-zinc-600 sm:max-w-[280px] dark:border-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-300">
              {chartLocationLabel}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="px-2 py-0.5 rounded border border-zinc-300 bg-white/80 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-200 dark:hover:bg-zinc-800"
              onClick={()=> { setEditingLoc(v=>!v); setLocInput(data?.location || ''); }}
            >
              Edit
            </button>
            <button
              type="button"
              disabled={!!snapDisabled}
              className="px-2.5 py-0.5 rounded-full border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 disabled:hover:bg-blue-50 dark:border-sky-500/40 dark:bg-sky-500/10 dark:text-sky-200 dark:hover:bg-sky-500/20"
              onClick={onSnap}
            >
              Snap
            </button>
            {showForensicButton && (
              <>
                <button
                  type="button"
                  className="px-1.5 py-0.5 rounded-lg border text-[11px]
                             bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                             dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
                  onClick={onForensic}
                >Forensic</button>
                <button
                  type="button"
                  className="px-1.5 py-0.5 rounded-lg border text-[11px]
                             bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                             dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
                  onClick={onCasePrompt || defaultCasePrompt}
                  title="Copy AI-ready case prompt"
                >Case Prompt</button>
              </>
            )}
          </div>
        </div>
      </div>
      {editingLoc && (
        <div className="mb-2 flex items-center gap-2 text-[11px]">
          <input value={locInput} onChange={e=>setLocInput(e.target.value)} className="px-2 py-1 border rounded w-60" placeholder="City, Country or lat,lon" />
          <button type="button" className="px-2 py-1 rounded border border-zinc-300 hover:bg-zinc-50" onClick={async ()=> { try { await onLocationChange?.(locInput); } catch(_){} finally { setEditingLoc(false); } }}>Set</button>
          <button type="button" className="px-2 py-1 text-zinc-600" onClick={()=> setEditingLoc(false)}>Cancel</button>
        </div>
      )}
      <div className={`relative w-full aspect-square rounded-lg text-zinc-500`}>
        {/* SketchWheel fills the square */}
        <div className="absolute inset-0">
          <SketchWheel asc={asc} cusps={cusps} planets={planets} showAspects={false} />
        </div>
        {/* Hour-of-Day mini ring bottom-right */}
        <div className="absolute right-2 bottom-2 w-20 h-20 rounded-full grid place-items-center" style={{ background: `conic-gradient(#111827 ${angle}deg, #e5e7eb ${angle}deg 360deg)` }}>
          <div className="bg-white rounded-full w-14 h-14 grid place-items-center text-center">
            <div className="text-[10px] leading-3">
              {hours?.current_hour?.ruling_planet && (
                <div className="text-base leading-none">{planetGlyphs[hours.current_hour.ruling_planet] || ''}</div>
              )}
              <div className="text-xs font-semibold">
                {(() => {
                  try {
                    return new Intl.DateTimeFormat(TIME_LOCALE, {
                      hour: '2-digit',
                      minute: '2-digit',
                      hour12: false,
                      hourCycle: 'h23'
                    }).format(clockDt);
                  } catch {
                    return clockDt.toISOString().slice(11, 16);
                  }
                })()}
              </div>
              <div className="text-[10px] text-zinc-500">Hr of Day</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
  );
}

function MoonCondition({ data }){
  const moon = data?.moon;
  const t = data?.moon_timeline || {};
  const left = moon ? `${degString(moon.longitude)} ${moon.sign}` : '-';
  // Compute basic Moon phase from Sun/Moon elongation (client-side)
  const phaseInfo = (() => {
    try {
      const planets = Array.isArray(data?.planets) ? data.planets : [];
      const m = planets.find(p => p?.planet === 'Moon');
      const s = planets.find(p => p?.planet === 'Sun');
      const mLon = Number(m?.longitude);
      const sLon = Number(s?.longitude);
      if (!isFinite(mLon) || !isFinite(sLon)) return null;
      const norm = (x) => ((x % 360) + 360) % 360;
      const D = norm(mLon - sLon); // elongation
      const illum = Math.max(0, Math.min(1, (1 - Math.cos(D * Math.PI/180)) / 2));
      const pct = Math.round(illum * 100);
      const near = (a, b, tol=8) => Math.abs(norm(a - b)) <= tol;
      let name = '';
      if (near(D, 0)) name = 'New Moon';
      else if (near(D, 90)) name = 'First Quarter';
      else if (near(D, 180)) name = 'Full Moon';
      else if (near(D, 270)) name = 'Last Quarter';
      else if (D > 0 && D < 90) name = 'Waxing Crescent';
      else if (D > 90 && D < 180) name = 'Waxing Gibbous';
      else if (D > 180 && D < 270) name = 'Waning Gibbous';
      else name = 'Waning Crescent';
      const waxing = D < 180;
      return { name, pct, waxing };
    } catch { return null; }
  })();
  // Format hours to a friendly string, e.g., 1d 5h or 2h 10m
  const fmtH = (h) => {
    if (h == null) return '-';
    const d = Math.floor(h/24); const hr = Math.floor(h%24); const m = Math.round((h*60)%60);
    if (d>0) return `${d}d ${hr}h`;
    if (hr>0) return `${hr}h ${m}m`;
    return `${m}m`;
  };
  // Map aspect numeric/name to canonical name
  const aspectLabel = (val) => {
    if (typeof val === 'string' && val) return val; // already a name like 'Trine'
    const n = typeof val === 'number' ? val : Number(val);
    if (!isFinite(n)) return String(val ?? '');
    if (Math.abs(n - 0) < 1e-6) return 'Conjunction';
    if (Math.abs(n - 60) < 1e-6) return 'Sextile';
    if (Math.abs(n - 90) < 1e-6) return 'Square';
    if (Math.abs(n - 120) < 1e-6) return 'Trine';
    if (Math.abs(n - 180) < 1e-6) return 'Opposition';
    return `${n}\u00B0`;
  };
  const vocTag = t.in_voc
    ? `VoC ends in ${fmtH(t.sign_exit_eta_hours)}`
    : (t.voc_starts_in_hours != null
        ? (t.voc_starts_in_hours <= (1/60) ? 'VoC now' : `VoC in ${fmtH(t.voc_starts_in_hours)}`)
        : 'VoC in -');
  const start = t.next_aspect?.eta_hours != null
    ? `Next ${PlanetSymbols.Moon} ${aspectSymbol(aspectLabel(t.next_aspect.aspect))} ${(PlanetSymbols[t.next_aspect.planet] || t.next_aspect.planet)} in ${fmtH(t.next_aspect.eta_hours)}`
    : '-';
  const next = t.sign_exit_eta_hours != null ? `Next sign ${fmtH(t.sign_exit_eta_hours)}` : '-';
  const prog = typeof t.sign_progress_pct === 'number' ? Math.max(0, Math.min(100, t.sign_progress_pct)) : 0;
  return (
    <div className={panelCls}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">Moon Condition</h3>
      </div>
      <div className="flex items-start justify-between gap-4">
        <div className="text-sm">
          <div className="font-medium">{left}</div>
          <div className="text-xs text-zinc-500">{vocTag}</div>
          {phaseInfo && (
            <div className="mt-1 text-xs text-zinc-700">
              <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white">{phaseInfo.name} · {phaseInfo.pct}%</span>
            </div>
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-end gap-2 text-xs text-zinc-700">
            <span className="px-2 py-0.5 rounded-full border border-zinc-200">{start}</span>
            <span>{'->'}</span>
            <span className="px-2 py-0.5 rounded-full border border-zinc-200">{next}</span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-zinc-200 overflow-hidden">
            <div className="h-full bg-zinc-900" style={{ width: `${prog}%` }} />
          </div>
          <div className="mt-2 flex items-center gap-2 text-[11px] text-zinc-600">
            <span className="px-1.5 py-0.5 rounded-full border border-zinc-200">VoC: {(t?.in_voc ?? moon?.void_of_course) ? 'Yes' : 'No'}</span>
            <span className="px-1.5 py-0.5 rounded-full border border-zinc-200">dur. {t.voc_duration_hours!=null? fmtH(t.voc_duration_hours): '-'}</span>
            <span className="text-zinc-500">
              {t?.next_aspect ? (
                <>
                  {PlanetSymbols.Moon} {aspectSymbol(aspectLabel(t.next_aspect.aspect))} {PlanetSymbols[t.next_aspect.planet] || t.next_aspect.planet}
                </>
              ) : '-'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SavedSnapsTile({ snaps, loading, loaded, onRefresh, onLoad, onDelete }){
  const [mode, setMode] = useState('snaps'); // 'snaps' | 'search'
  const [q, setQ] = useState('');
  const [idxLoading, setIdxLoading] = useState(false);
  const [indexDocs, setIndexDocs] = useState(null); // [{ id, snap, text, title, subtitle }]
  const [actionBusy, setActionBusy] = useState(null); // id of snap being acted on

  const handleLoad = async (snap) => {
    try { setActionBusy(snap.id); await onLoad(snap); } catch (e) { /* no-op */ } finally { setActionBusy(null); }
  };
  const handleDelete = async (id) => {
    try { setActionBusy(id); await onDelete(id); } catch (e) { /* no-op */ } finally { setActionBusy(null); }
  };

  // Build index on demand when entering search
  useEffect(() => {
    let cancelled = false;
    const build = async () => {
      if (mode !== 'search' || indexDocs !== null || !Array.isArray(snaps) || snaps.length === 0) return;
      setIdxLoading(true);
      try {
        // Fetch full snap details concurrently with small batch size
        const ids = snaps.map(s => s.id);
        const batch = async (arr, size) => {
          const out = [];
          for (let i = 0; i < arr.length; i += size) {
            const group = arr.slice(i, i + size).map(async (id) => {
              try { const res = await AstroClockAPI.getSnap(id); return res?.snap; } catch { return null; }
            });
            const results = await Promise.all(group);
            out.push(...results.filter(Boolean));
            if (cancelled) break;
          }
          return out;
        };
        const fullSnaps = await batch(ids, 5);
        if (cancelled) return;
        const docs = fullSnaps.map((s) => {
          const dash = s?.dashboard || {};
          const parts = [];
          // Basic
          if (s?.label) parts.push(`label:${s.label}`);
          if (s?.location) parts.push(`loc:${s.location}`);
          if (s?.summary?.chart_sect) parts.push(`sect:${s.summary.chart_sect}`);
          if (s?.summary?.sect_light) parts.push(`light:${s.summary.sect_light}`);
          if (s?.summary?.hour_ruler) parts.push(`hour:${s.summary.hour_ruler}`);
          if (s?.summary?.moon_sign) parts.push(`moon:${s.summary.moon_sign}`);
          // Planets
          const planets = Array.isArray(dash.planets) ? dash.planets : [];
          planets.forEach(p => {
            const name = p.planet || p.name;
            const sign = p.sign || '';
            const house = (p.house != null) ? `H${p.house}` : '';
            parts.push(`${name} ${sign} ${house}`);
          });
          // Aspects
          const aspects = Array.isArray(dash.top_aspects) ? dash.top_aspects : [];
          const tight = dash.tightest_aspect ? [dash.tightest_aspect] : [];
          [...aspects, ...tight].forEach(a => {
            if (!a) return;
            const aName = (a.aspect || '').toString();
            const p1 = a.planet1 || '';
            const p2 = a.planet2 || '';
            parts.push(`${p1} ${aName} ${p2}`);
          });
          const text = parts.join(' ').toLowerCase();
          const title = s?.label || 'Untitled Snap';
          const subtitle = `${new Date(s.effective_datetime).toLocaleString()} · ${s.location || '-'}`;
          return { id: s.id, snap: s, text, title, subtitle };
        });
        setIndexDocs(docs);
      } finally {
        if (!cancelled) setIdxLoading(false);
      }
      return () => { cancelled = true; };
    };
    build();
    return () => { cancelled = true; };
  }, [mode, indexDocs, snaps]);

  // Filter results
  const results = useMemo(() => {
    if (mode !== 'search' || !indexDocs) return [];
    const qq = (q || '').trim().toLowerCase();
    if (!qq) return indexDocs.slice(0, 50);
    const tokens = qq.split(/\s+/).filter(Boolean);
    return indexDocs.filter(doc => tokens.every(t => doc.text.includes(t))).slice(0, 100);
  }, [mode, indexDocs, q]);

  return (
    <div className={panelCls}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">Saved Snaps</h3>
        <div className="flex items-center gap-2">
          <button onClick={onRefresh} className="text-[11px] text-zinc-600 px-2 py-0.5 rounded border border-zinc-300 hover:bg-zinc-50">Refresh</button>
          <button onClick={() => setMode(m => m === 'snaps' ? 'search' : 'snaps')} className="text-[11px] text-zinc-600 px-2 py-0.5 rounded border border-zinc-300 hover:bg-zinc-50">{mode==='snaps' ? 'Search' : 'Snaps'}</button>
        </div>
      </div>

      {mode === 'snaps' ? (
        loading ? (
          <div className="text-sm text-zinc-500">Loading…</div>
        ) : !loaded ? (
          <div className="text-sm text-zinc-500">Saved snaps are not loaded yet. Click Refresh when you need them.</div>
        ) : (snaps?.length || 0) === 0 ? (
          <div className="text-sm text-zinc-500">No snaps yet</div>
        ) : (
          <div className="space-y-2 max-h-72 overflow-auto pr-1">
            {snaps.map((s)=> (
              <div key={s.id} className="border border-zinc-200 rounded p-2 flex items-center justify-between">
                <div className="text-sm">
                  <div className="font-medium">{s.label || 'Untitled Snap'}</div>
                  <div className="text-[11px] text-zinc-600">{(new Date(s.effective_datetime)).toLocaleString()} · {s.location || '-'}</div>
                  <div className="text-[11px] text-zinc-600">Hour: {s.summary?.hour_ruler || '-'} · Moon: {s.summary?.moon_sign || '-'}</div>
                  <div className="text-[11px] text-zinc-600">Sect: {s.summary?.chart_sect ? (s.summary.chart_sect === 'diurnal' ? 'Day' : 'Night') : '-'}{s.summary?.sect_light ? ` · Light: ${s.summary.sect_light}` : ''}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button disabled={actionBusy===s.id} className="px-2 py-0.5 text-[11px] rounded border border-zinc-300 hover:bg-zinc-50 disabled:opacity-50" onClick={()=> handleLoad(s)}>{actionBusy===s.id? '…':'Load'}</button>
                  <button disabled={actionBusy===s.id} className="px-2 py-0.5 text-[11px] rounded border border-zinc-300 text-zinc-700 hover:bg-zinc-50 disabled:opacity-50" onClick={()=> handleDelete(s.id)}>{actionBusy===s.id? '…':'Delete'}</button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search label, planet (e.g., Sun Leo H10), or aspect (e.g., Moon trine Venus)" className="w-full px-2 py-1 border rounded" />
            <button className="text-[11px] px-2 py-1 border rounded" onClick={()=>setQ('')}>Clear</button>
          </div>
          {idxLoading ? (
            <div className="text-sm text-zinc-500">Building index…</div>
          ) : (!indexDocs || indexDocs.length === 0) ? (
            <div className="text-sm text-zinc-500">No snaps to search</div>
          ) : results.length === 0 ? (
            <div className="text-sm text-zinc-500">No matches</div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-auto pr-1">
              {results.map(doc => (
                <div key={doc.id} className="border border-zinc-200 rounded p-2 flex items-center justify-between">
                  <div className="text-sm">
                    <div className="font-medium">{doc.title}</div>
                    <div className="text-[11px] text-zinc-600">{doc.subtitle}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button disabled={actionBusy===doc.id} className="px-2 py-0.5 text-[11px] rounded border border-zinc-300 hover:bg-zinc-50 disabled:opacity-50" onClick={()=> handleLoad(doc.snap)}>{actionBusy===doc.id? '…':'Load'}</button>
                    <button disabled={actionBusy===doc.id} className="px-2 py-0.5 text-[11px] rounded border border-zinc-300 text-zinc-700 hover:bg-zinc-50 disabled:opacity-50" onClick={()=> handleDelete(doc.id)}>{actionBusy===doc.id? '…':'Delete'}</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CurrentAspectCard({ data, onOpenAnalysis, useMorin, setUseMorin }){
  const listStandard = (data?.planetary_aspects_precise && data.planetary_aspects_precise.length > 0)
    ? data.planetary_aspects_precise.slice(0,4)
    : (data?.top_aspects && data.top_aspects.length > 0)
    ? data.top_aspects.slice(0,4)
    : (data?.tightest_aspect ? [data.tightest_aspect] : []);
  const getMaxOrb = (name) => {
    const key = (name||'').toLowerCase();
    // Declination aspects (parallel / antiparallel) use much tighter orb by default
    if (key.includes('parallel')) return 1; // 1° default for declination parallels
    if (key.includes('conj')) return 8;
    if (key.includes('opp')) return 8;
    if (key.includes('square')) return 8;
    if (key.includes('trine')) return 8;
    if (key.includes('sext')) return 6;
    if (key.includes('semi') && key.includes('sext')) return 3; // semi-sextile (tighter window)
    if (key.includes('quin')) return 4; // quincunx
    return 6;
  };
  const [useDecl, setUseDecl] = useState(false);
  const declList = (data?.top_declinations || []).slice(0,4);
  const morinAntiList = (data?.morin_antiscia || []).slice(0,4);
  const morinList = Array.isArray(data?.morin_aspects) ? data.morin_aspects.slice(0,4) : [];
  const aspects = useDecl ? (useMorin ? morinAntiList : declList) : (useMorin ? morinList : listStandard);
  const title = useDecl
    ? (useMorin ? 'Antiscia (Morin)' : 'Declination (∥ / antiparallel)')
    : (useMorin ? 'Morin Aspects' : 'Current Aspects');
  return (
    <div data-testid="current-aspects-card" className={`${panelCls} aspect-square flex flex-col overflow-hidden`}>
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="font-semibold text-sm">{title}</h3>
        <div className="flex flex-wrap items-center justify-end gap-3 text-[11px] text-zinc-600">
          <div className="flex items-center gap-1">
            <span className="hidden sm:inline">Morin</span>
            <label className="relative inline-flex items-center cursor-pointer select-none">
              <input data-testid="current-aspects-morin-toggle" type="checkbox" className="sr-only peer" checked={useMorin} onChange={()=> { setUseMorin(v=>!v); }} />
              <div className="w-10 h-5 bg-zinc-300 peer-checked:bg-zinc-800 rounded-full transition-colors"></div>
              <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
            </label>
          </div>
          <div className="flex items-center gap-1">
            <span className="hidden sm:inline">Decl</span>
            <label className="relative inline-flex items-center cursor-pointer select-none">
              <input type="checkbox" className="sr-only peer" checked={useDecl} onChange={()=> { setUseDecl(v=>!v); }} />
              <div className="w-10 h-5 bg-zinc-300 peer-checked:bg-zinc-800 rounded-full transition-colors"></div>
              <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
            </label>
          </div>
        </div>
      </div>
      {aspects.length === 0 ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="text-sm text-zinc-500">No major aspects</div>
          <div className="mt-auto flex items-center justify-end border-t border-zinc-100 pt-2">
            <button type="button" onClick={onOpenAnalysis}
                    className="shrink-0 rounded border border-zinc-300 bg-white/80 px-2 py-0.5 text-[11px] hover:bg-white/90"
                    title="Open comprehensive aspect analysis">More</button>
          </div>
        </div>
      ) : (
        <>
          <div className="astro-scroll-shell min-h-0 flex-1">
            <div data-testid="current-aspects-scroll" className="astro-scroll min-h-0 flex-1">
              <div className="space-y-3 pb-2">
                {aspects.map((a, idx) => {
                  let percent = 0;
                  try {
                    const max = Number(a?.max_orb ?? getMaxOrb(a?.aspect));
                    const orb = Math.abs(Number(a?.orb || 0));
                    percent = Math.max(0, Math.min(100, (1 - (orb / (max || 6))) * 100));
                  } catch {}
                  return (
                    <div key={idx}>
                      <div className="text-sm font-semibold">{a.planet1} {a.symbol || ''} {a.planet2}</div>
                      <div className="text-xs leading-5 text-zinc-600">orb {a.orb_text || `${Math.abs(Number(a?.orb||0)).toFixed(2)}°`} / max {(a?.max_orb ?? getMaxOrb(a?.aspect))}°{useMorin && (a?.partile ? ' · partile' : (a?.complete_platic ? ' · platic' : ''))}{useMorin && a?.direction ? ` · ${a.direction}` : ''}{useMorin && a?.phase ? ` · ${a.phase}` : ''}</div>
                      <div className="mt-1 flex items-center justify-between text-[11px]"><span>Exactness</span><span>{Math.round(percent)}%</span></div>
                      <div className="mt-0.5 h-2 overflow-hidden rounded-full bg-zinc-200">
                        <div className="h-full bg-zinc-900" style={{ width: `${percent}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="mt-2 flex shrink-0 items-end justify-between gap-3 border-t border-zinc-100 pt-2">
            <div className="text-[11px] leading-4 text-zinc-500">Bar fills as orb tightens toward exact.</div>
            <button type="button" onClick={onOpenAnalysis}
                    className="shrink-0 rounded border border-zinc-300 bg-white/80 px-2 py-0.5 text-[11px] hover:bg-white/90"
                    title="Open comprehensive aspect analysis">More</button>
          </div>
        </>
      )}
    </div>
  );
}

function PositionsDignityCard({ data }){
  const [sort, setSort] = useState('score');
  const rows = (data?.planets||[]).slice().sort((a,b)=>{
    if (sort==='lon') return (a.longitude||0)-(b.longitude||0);
    const sa = Number(a.dignity_score)||0; const sb = Number(b.dignity_score)||0; return sb-sa;
  });
  const norm = (score)=> Math.max(-5, Math.min(5, Number(score)||0));
  const knobLeft = (score)=> `calc( ${( (norm(score) - (-5)) / 10 ) * 100}% - 8px )`;
  return (
    <div className={`${panelCls} aspect-square`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">Positions + Dignity</h3>
        <div className="text-[11px] text-zinc-600 space-x-2">
          <button onClick={()=>setSort('score')} className={`px-1.5 py-0.5 rounded border ${sort==='score'? 'border-zinc-800 text-zinc-800':'border-zinc-200'}`}>By Score</button>
          <button onClick={()=>setSort('lon')} className={`px-1.5 py-0.5 rounded border ${sort==='lon'? 'border-zinc-800 text-zinc-800':'border-zinc-200'}`}>By Longitude</button>
        </div>
      </div>
      <div className="overflow-auto h-[calc(100%-32px)] pr-1">
        <div className="space-y-2">
          {rows.map((p, idx)=>{
            const s = Number(p.dignity_score)||0;
            const sign = p.sign || signFromLon(p.longitude);
            return (
              <div key={idx} className="py-1 border-b border-zinc-100 last:border-0">
                <div className="grid grid-cols-12 items-center gap-2">
                  <div className="col-span-3 flex items-center space-x-2">
                    <span className="text-lg leading-none">{PlanetSymbols[p.planet] || '·'}{p.retrograde? ' R':''}</span>
                    <span className="font-medium text-sm">{p.planet}</span>
                  </div>
                  <div className="col-span-4 text-sm">
                    {degreeTextFromLon(p.longitude)} {sign} - <span className="px-1.5 py-0.5 rounded border border-zinc-200 text-xs">H{p.house??'-'}</span>
                  </div>
                  <div className="col-span-3">
                    <div className="relative h-3 rounded-full" style={{ background: 'linear-gradient(90deg, var(--grad-left,#fecdd3), var(--grad-mid,#e5e7eb), var(--grad-right,#bbf7d0))' }}>
                      <div className="absolute inset-y-0 left-1/2 w-px bg-zinc-400/70" />
                      <div className="absolute -top-1 -bottom-1 w-4 rounded-full border border-zinc-800/30 bg-white" style={{ left: knobLeft(s) }} />
                    </div>
                  </div>
                  <div className="col-span-2 text-sm text-right">
                    <span className={`${s>=0?'text-emerald-700':'text-rose-700'}`}>{s>=0? '+':''}{s}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
