import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, FileSpreadsheet, Play, RefreshCw, UploadCloud } from 'lucide-react';

import { AstroClockAPI } from '../astroclock/api.mjs';
import {
  ConsoleBracketEyebrow,
  ConsoleStatusBadge,
  ResearchSectionIntro,
  toneBadgeClass,
} from '../astroclock/researchWorkspacePrimitives.jsx';

const astroPageShellCls = 'max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8';
const astroPanelCls = 'rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900/70';
const astroTableFrameCls = 'overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-700 dark:bg-zinc-900/70';
const astroInputCls = 'w-full rounded-2xl border border-zinc-200 bg-white px-3 py-1.5 text-[13px] text-zinc-900 shadow-none outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-100 dark:border-zinc-700 dark:bg-zinc-900/70 dark:text-zinc-100 dark:focus:border-zinc-500 dark:focus:ring-zinc-800';
const astroSecondaryButtonCls = 'rounded-full border border-zinc-200 bg-white px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-700 shadow-sm hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900/70 dark:text-zinc-100 dark:hover:border-zinc-500 dark:hover:bg-zinc-900';
const astroPrimaryButtonCls = 'inline-flex min-h-9 items-center justify-center rounded-full border border-zinc-900 bg-zinc-900 px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-white shadow-sm hover:border-zinc-800 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-300 disabled:text-zinc-50 dark:border-white dark:bg-white dark:text-zinc-900 dark:hover:border-zinc-200 dark:hover:bg-zinc-200 dark:disabled:border-zinc-700 dark:disabled:bg-zinc-700 dark:disabled:text-zinc-300';

function ResearchStat({ label, value }) {
  return (
    <div className="min-h-[74px] rounded-2xl border border-zinc-200 bg-white px-3.5 py-3 text-sm shadow-sm dark:border-zinc-700 dark:bg-zinc-900/70">
      <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400 dark:text-zinc-500">{label}</div>
      <div className="mt-2 text-[1.15rem] font-semibold leading-tight tracking-[-0.02em] text-zinc-900 dark:text-zinc-50">{value}</div>
    </div>
  );
}

const DEFAULT_FAMILIES = [
  'positions',
  'houses',
  'aspects',
  'rulership',
  'receptions',
  'dispositors',
  'dignities',
  'motion',
  'solar',
  'points',
  'lots',
  'fixed_stars',
  'asteroids',
  'midpoints',
  'directional_3d',
];

const DEFAULT_SCOPE_BY_FAMILY = {
  positions: 'planet_signs',
  houses: 'planet_houses',
  aspects: 'planetary_aspects',
  rulership: 'house_rulers',
  receptions: 'reception_pairs',
  dispositors: 'final_dispositors',
  dignities: 'dignity_status',
  motion: 'direction',
  solar: 'solar_conditions',
  points: 'active_points',
  lots: 'lot_signs',
  fixed_stars: 'star_hits',
  asteroids: 'asteroid_signs',
  midpoints: 'midpoint_signs',
  directional_3d: 'horizon_state',
};

const FALLBACK_SCOPES_BY_FAMILY = {
  positions: [
    ['planet_signs', 'Planet signs'],
    ['elements', 'Elements'],
    ['modalities', 'Modalities'],
    ['zodiac_range', 'Custom zodiac range', true],
  ],
  houses: [['planet_houses', 'Planet houses'], ['angle_signs', 'Angle signs'], ['cusp_signs', 'Cusp signs']],
  aspects: [['planetary_aspects', 'Planetary aspects'], ['angle_aspects', 'Angle aspects']],
  rulership: [['house_rulers', 'House rulers'], ['ruler_houses', 'Ruler houses']],
  receptions: [['reception_pairs', 'Reception pairs']],
  dispositors: [['final_dispositors', 'Final dispositors']],
  dignities: [['dignity_status', 'Dignity status'], ['almutens', 'Almutens']],
  motion: [['direction', 'Direction'], ['stations', 'Stations']],
  solar: [['solar_conditions', 'Solar conditions'], ['solar_phases', 'Solar phases']],
  points: [['point_signs', 'Point signs'], ['active_points', 'Active points'], ['activation_contacts', 'Activation contacts']],
  lots: [['lot_signs', 'Lot signs'], ['lot_houses', 'Lot houses']],
  fixed_stars: [['star_hits', 'Star hits']],
  asteroids: [['asteroid_signs', 'Asteroid signs'], ['asteroid_motion', 'Asteroid motion']],
  midpoints: [['midpoint_signs', 'Midpoint signs']],
  directional_3d: [['horizon_state', 'Horizon state']],
};

function fallbackScopesForFamily(id) {
  return (FALLBACK_SCOPES_BY_FAMILY[id] || []).map(([scopeId, label, custom]) => ({
    id: scopeId,
    label,
    custom: Boolean(custom),
  }));
}

const FALLBACK_FAMILIES = DEFAULT_FAMILIES.map((id) => ({
  id,
  label: id.replace(/_/g, ' '),
  default_scopes: DEFAULT_SCOPE_BY_FAMILY[id] ? [DEFAULT_SCOPE_BY_FAMILY[id]] : [],
  scopes: fallbackScopesForFamily(id),
}));

const RESEARCH_OBJECT_OPTIONS = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto'];
const ZODIAC_SIGN_OPTIONS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];

const COLUMN_ALIASES = {
  name: ['name', 'label', 'chart_name', 'chart name', 'person', 'title'],
  datetime: ['datetime', 'date_time', 'date time', 'timestamp', 'birth_datetime', 'birth datetime'],
  date: ['date', 'birth_date', 'birth date'],
  time: ['time', 'birth_time', 'birth time'],
  location: ['location', 'place', 'city', 'birth_place', 'birth place'],
  timezone: ['timezone', 'time_zone', 'time zone', 'tz'],
  latitude: ['latitude', 'lat'],
  longitude: ['longitude', 'lon', 'lng'],
  chart_type: ['chart_type', 'chart type', 'type'],
  group: ['group', 'cohort', 'tag'],
  notes: ['notes', 'note', 'description'],
};

function cleanText(value) {
  return String(value ?? '').trim();
}

function normalizeHeader(value) {
  return cleanText(value).toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');
}

function pickColumn(row, key) {
  const aliases = COLUMN_ALIASES[key] || [key];
  const normalizedMap = new Map(Object.keys(row || {}).map((column) => [normalizeHeader(column), column]));
  for (const alias of aliases) {
    const actual = normalizedMap.get(normalizeHeader(alias));
    if (actual != null) return row[actual];
  }
  return '';
}

export function normalizeResearchImportRows(rows) {
  return (Array.isArray(rows) ? rows : [])
    .map((row, index) => ({
      name: cleanText(pickColumn(row, 'name')) || `Chart ${index + 1}`,
      datetime: cleanText(pickColumn(row, 'datetime')),
      date: cleanText(pickColumn(row, 'date')),
      time: cleanText(pickColumn(row, 'time')),
      location: cleanText(pickColumn(row, 'location')),
      timezone: cleanText(pickColumn(row, 'timezone')),
      latitude: cleanText(pickColumn(row, 'latitude')),
      longitude: cleanText(pickColumn(row, 'longitude')),
      chart_type: cleanText(pickColumn(row, 'chart_type')) || 'natal',
      group: cleanText(pickColumn(row, 'group')),
      notes: cleanText(pickColumn(row, 'notes')),
    }))
    .filter((row) => (
      row.name
      || row.datetime
      || row.date
      || row.time
      || row.location
      || row.latitude
      || row.longitude
    ));
}

export async function parseResearchWorkbook(buffer) {
  const { read, utils } = await import('xlsx');
  const workbook = read(buffer, { type: 'array', cellDates: false });
  const firstSheetName = workbook.SheetNames[0];
  if (!firstSheetName) return [];
  const sheet = workbook.Sheets[firstSheetName];
  const rawRows = utils.sheet_to_json(sheet, { defval: '' });
  return normalizeResearchImportRows(rawRows);
}

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  return `${Math.round(number * 1000) / 10}%`;
}

function formatNumber(value, digits = 4) {
  if (value === 'inf') return 'inf';
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  return number.toFixed(digits);
}

function warningLabel(value) {
  return String(value || '').replace(/_/g, ' ');
}

function normalizeDegreeValue(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(30, number));
}

function degreeLabel(value) {
  const number = normalizeDegreeValue(value);
  if (Math.abs(number - Math.round(number)) < 0.000001) return String(Math.round(number));
  return number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
}

function featureScopeKey(scope) {
  if (scope?.kind === 'zodiac_range') {
    return [
      'range',
      scope.family,
      scope.object,
      scope.sign,
      degreeLabel(scope.start_degree),
      degreeLabel(scope.end_degree),
    ].join(':');
  }
  return ['preset', scope?.family, scope?.preset].join(':');
}

function findScopeDefinition(families, familyId, presetId) {
  const family = families.find((item) => item.id === familyId);
  return (family?.scopes || []).find((scope) => scope.id === presetId);
}

function featureScopeLabel(families, scope) {
  const family = families.find((item) => item.id === scope?.family);
  if (scope?.kind === 'zodiac_range') {
    return `${scope.object} in ${scope.sign} ${degreeLabel(scope.start_degree)}-${degreeLabel(scope.end_degree)}`;
  }
  const preset = findScopeDefinition(families, scope?.family, scope?.preset);
  const label = preset?.label || String(scope?.preset || '').replace(/_/g, ' ');
  return `${family?.label || scope?.family}: ${label}`;
}

function familyDefaultScopes(family) {
  const defaults = Array.isArray(family?.default_scopes) ? family.default_scopes : [];
  if (defaults.length) return defaults;
  const firstPreset = (Array.isArray(family?.scopes) ? family.scopes : []).find((scope) => !scope?.custom);
  if (firstPreset?.id) return [firstPreset.id];
  return DEFAULT_SCOPE_BY_FAMILY[family?.id] ? [DEFAULT_SCOPE_BY_FAMILY[family.id]] : [];
}

function buildDefaultFeatureScopes(families) {
  return (Array.isArray(families) ? families : [])
    .flatMap((family) => familyDefaultScopes(family).map((preset) => ({ family: family.id, preset })));
}

function normalizeCatalogFamilies(families) {
  const rows = Array.isArray(families) && families.length ? families : FALLBACK_FAMILIES;
  return rows.map((family) => ({
    ...family,
    default_scopes: familyDefaultScopes(family),
    scopes: Array.isArray(family.scopes) && family.scopes.length
      ? family.scopes
      : fallbackScopesForFamily(family.id),
  }));
}

function normalizeFeatureScopeForRequest(scope) {
  if (scope?.kind === 'zodiac_range') {
    return {
      family: 'positions',
      kind: 'zodiac_range',
      object: scope.object,
      sign: scope.sign,
      start_degree: normalizeDegreeValue(scope.start_degree),
      end_degree: normalizeDegreeValue(scope.end_degree),
    };
  }
  return {
    family: scope.family,
    preset: scope.preset,
  };
}

export function isResearchRowReady(row) {
  const hasTime = Boolean(cleanText(row?.datetime) || (cleanText(row?.date) && cleanText(row?.time)));
  const hasLocation = Boolean(cleanText(row?.location));
  const hasLatitude = cleanText(row?.latitude) !== '';
  const hasLongitude = cleanText(row?.longitude) !== '';
  return hasTime && (hasLocation || (hasLatitude && hasLongitude));
}

function sampleRows() {
  return [
    {
      name: 'Sample A',
      date: '1990-01-13',
      time: '21:33',
      location: 'Jerusalem, Israel',
      timezone: 'Asia/Jerusalem',
      chart_type: 'natal',
    },
    {
      name: 'Sample B',
      date: '1988-04-02',
      time: '06:15',
      location: 'London, United Kingdom',
      timezone: 'Europe/London',
      chart_type: 'natal',
    },
    {
      name: 'Sample C',
      date: '1977-10-21',
      time: '14:40',
      location: 'New York, United States',
      timezone: 'America/New_York',
      chart_type: 'event',
    },
  ];
}

export default function ResearchWorkspace({ darkMode = false }) {
  const [families, setFamilies] = useState([]);
  const [activeFamilyId, setActiveFamilyId] = useState('positions');
  const [selectedFeatureScopes, setSelectedFeatureScopes] = useState(() => buildDefaultFeatureScopes(FALLBACK_FAMILIES));
  const [rangeDraft, setRangeDraft] = useState({
    object: 'Sun',
    sign: 'Aries',
    start_degree: 0,
    end_degree: 10,
  });
  const [rows, setRows] = useState([]);
  const [fileName, setFileName] = useState('');
  const [importError, setImportError] = useState('');
  const [controlsPerChart, setControlsPerChart] = useState(20);
  const [yearWindow, setYearWindow] = useState(3);
  const [seed, setSeed] = useState('vox-stella-research');
  const [houseSystem, setHouseSystem] = useState('P');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    let cancelled = false;
    AstroClockAPI.listResearchEvaluators()
      .then((response) => {
        if (cancelled) return;
        const nextFamilies = response?.success ? (response.data?.families || []) : [];
        const normalized = normalizeCatalogFamilies(nextFamilies);
        setFamilies(normalized);
        setSelectedFeatureScopes(buildDefaultFeatureScopes(normalized));
        setActiveFamilyId((current) => (normalized.some((family) => family.id === current) ? current : (normalized[0]?.id || 'positions')));
      })
      .catch(() => {
        if (!cancelled) {
          const fallback = normalizeCatalogFamilies([]);
          setFamilies(fallback);
          setSelectedFeatureScopes(buildDefaultFeatureScopes(fallback));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeFamilies = useMemo(() => normalizeCatalogFamilies(families), [families]);
  const activeFamily = activeFamilies.find((family) => family.id === activeFamilyId) || activeFamilies[0] || FALLBACK_FAMILIES[0];
  const selectedFeatureKeys = useMemo(
    () => new Set(selectedFeatureScopes.map(featureScopeKey)),
    [selectedFeatureScopes],
  );
  const validRowCount = rows.filter(isResearchRowReady).length;
  const featureScopesForRequest = useMemo(
    () => selectedFeatureScopes.map(normalizeFeatureScopeForRequest),
    [selectedFeatureScopes],
  );
  const selectedFamilyList = useMemo(
    () => Array.from(new Set(featureScopesForRequest.map((scope) => scope.family))).sort(),
    [featureScopesForRequest],
  );
  const signals = Array.isArray(result?.signals) ? result.signals : [];
  const manifest = result?.manifest || {};
  const statistics = result?.statistics || {};

  const addFeatureScope = (scope) => {
    const normalized = normalizeFeatureScopeForRequest(scope);
    const key = featureScopeKey(normalized);
    setSelectedFeatureScopes((current) => {
      if (current.some((item) => featureScopeKey(item) === key)) return current;
      return [...current, normalized];
    });
  };

  const removeFeatureScope = (scope) => {
    const key = featureScopeKey(scope);
    setSelectedFeatureScopes((current) => current.filter((item) => featureScopeKey(item) !== key));
  };

  const addRangeFeature = () => {
    addFeatureScope({
      family: 'positions',
      kind: 'zodiac_range',
      object: rangeDraft.object,
      sign: rangeDraft.sign,
      start_degree: rangeDraft.start_degree,
      end_degree: rangeDraft.end_degree,
    });
  };

  const handleFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportError('');
    setResult(null);
    try {
      const parsed = await parseResearchWorkbook(await file.arrayBuffer());
      setRows(parsed);
      setFileName(file.name);
      if (!parsed.length) {
        setImportError('No chart rows were found in the first worksheet.');
      }
    } catch (nextError) {
      setImportError(nextError?.message || 'Unable to read this chart file.');
    } finally {
      event.target.value = '';
    }
  };

  const runAnalysis = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await AstroClockAPI.runResearchAnalysis({
        charts: rows,
        evaluator_families: selectedFamilyList,
        feature_scopes: featureScopesForRequest,
        control: {
          strategy: 'matched_generated',
          per_chart: Number(controlsPerChart) || 20,
          year_window: Number(yearWindow) || 3,
          seed,
        },
        house_system_code: houseSystem,
        min_occurrence: 1,
      });
      if (!response?.success) {
        throw new Error(response?.error || response?.detail || 'Research analysis failed.');
      }
      setResult(response.data || {});
    } catch (nextError) {
      setError(nextError?.message || 'Research analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`${darkMode ? 'dark' : ''}`}>
      <div className={astroPageShellCls}>
          <section className="border-b border-zinc-200 pb-6 dark:border-zinc-700">
            <ConsoleBracketEyebrow module="default">research / chart_set</ConsoleBracketEyebrow>
            <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Research</h1>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                  Import a chart set, choose calculation families, and compare it against generated matched charts.
                </p>
              </div>
              <ConsoleStatusBadge label={loading ? 'Running' : result ? 'Results Ready' : 'Draft'} tone={loading ? 'accent' : result ? 'good' : 'default'} />
            </div>
          </section>

          <div className="mt-6 grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
            <aside className="space-y-4">
              <section className={astroPanelCls}>
                <ResearchSectionIntro
                  eyebrow="import"
                  title="Chart Set"
                  body="Use CSV, TSV, XLS, or XLSX with name, date/time or datetime, location, timezone, and optional coordinates."
                />
                <div className="mt-4 space-y-3">
                  <label className="flex min-h-[112px] cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-zinc-50/70 px-4 py-5 text-center text-sm text-zinc-600 hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-900/40 dark:text-zinc-300">
                    <UploadCloud className="mb-2 h-5 w-5" />
                    <span className="font-medium">Import chart file</span>
                    <span className="mt-1 text-xs text-slate-500">CSV, TSV, XLS, XLSX</span>
                    <input className="hidden" type="file" accept=".csv,.tsv,.xls,.xlsx" onChange={handleFile} />
                  </label>
                  <button
                    type="button"
                    className={astroSecondaryButtonCls}
                    onClick={() => {
                      setRows(sampleRows());
                      setFileName('sample chart set');
                      setImportError('');
                      setResult(null);
                    }}
                  >
                    <FileSpreadsheet className="mr-2 inline h-3.5 w-3.5" />
                    Load Sample
                  </button>
                  {fileName ? <div className="text-xs text-slate-500">Loaded: {fileName}</div> : null}
                  {importError ? (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                      {importError}
                    </div>
                  ) : null}
                </div>
              </section>

              <section className={astroPanelCls}>
                <ResearchSectionIntro
                  eyebrow="controls"
                  title="Generated Comparison"
                  body="Matched controls preserve chart context and randomize date/time with a saved seed."
                />
                <div className="mt-4 grid gap-3">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    Controls per chart
                    <input
                      className={`${astroInputCls} mt-1`}
                      type="number"
                      min="1"
                      max="100"
                      value={controlsPerChart}
                      onChange={(event) => setControlsPerChart(event.target.value)}
                    />
                  </label>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    Year window
                    <input
                      className={`${astroInputCls} mt-1`}
                      type="number"
                      min="0"
                      max="50"
                      value={yearWindow}
                      onChange={(event) => setYearWindow(event.target.value)}
                    />
                  </label>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    Seed
                    <input
                      className={`${astroInputCls} mt-1`}
                      value={seed}
                      onChange={(event) => setSeed(event.target.value)}
                    />
                  </label>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    House system
                    <select className={`${astroInputCls} mt-1`} value={houseSystem} onChange={(event) => setHouseSystem(event.target.value)}>
                      <option value="P">Placidus</option>
                      <option value="R">Regiomontanus</option>
                      <option value="W">Whole Sign</option>
                      <option value="E">Equal</option>
                      <option value="K">Koch</option>
                    </select>
                  </label>
                </div>
              </section>
            </aside>

            <main className="space-y-6">
              <section className={astroPanelCls}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <ResearchSectionIntro
                    eyebrow="features"
                    title="Research Features"
                    body="Build the exact feature list to test. Each tab adds explicit presets or custom conditions."
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className={astroSecondaryButtonCls}
                      onClick={() => {
                        setSelectedFeatureScopes(buildDefaultFeatureScopes(activeFamilies));
                      }}
                    >
                      All
                    </button>
                    <button
                      type="button"
                      className={astroSecondaryButtonCls}
                      onClick={() => {
                        setSelectedFeatureScopes([]);
                      }}
                    >
                      None
                    </button>
                  </div>
                </div>
                <div role="tablist" aria-label="Research feature families" className="mt-4 flex gap-2 overflow-x-auto border-b border-zinc-200 pb-2 dark:border-zinc-800">
                  {activeFamilies.map((family) => {
                    const selectedCount = selectedFeatureScopes.filter((scope) => scope.family === family.id).length;
                    const active = activeFamily?.id === family.id;
                    return (
                      <button
                        type="button"
                        role="tab"
                        aria-selected={active}
                        aria-controls={`research-feature-panel-${family.id}`}
                        key={family.id}
                        onClick={() => setActiveFamilyId(family.id)}
                        className={`shrink-0 rounded-full border px-3 py-2 text-left text-[11px] font-semibold transition ${
                          active
                            ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900'
                            : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900/40 dark:text-zinc-300'
                        }`}
                      >
                        <span className="block whitespace-nowrap">{family.label}</span>
                        <span className={`mt-0.5 block font-mono text-[9px] uppercase tracking-[0.14em] ${active ? 'text-zinc-200 dark:text-zinc-700' : 'text-zinc-400'}`}>
                          {selectedCount} selected
                        </span>
                      </button>
                    );
                  })}
                </div>
                <div
                  id={`research-feature-panel-${activeFamily?.id || 'positions'}`}
                  role="tabpanel"
                  className="mt-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-100 pb-4 dark:border-zinc-800">
                    <div>
                      <h5 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{activeFamily?.label}</h5>
                      {activeFamily?.description ? <p className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-300">{activeFamily.description}</p> : null}
                    </div>
                    <ConsoleStatusBadge label={`${selectedFeatureScopes.filter((scope) => scope.family === activeFamily?.id).length} selected`} />
                  </div>

                  <div className="mt-4">
                    <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400">presets</div>
                    <div className="mt-2 divide-y divide-zinc-100 border-y border-zinc-100 dark:divide-zinc-800 dark:border-zinc-800">
                      {(activeFamily?.scopes || []).filter((scope) => !scope.custom).map((scope) => {
                        const payload = { family: activeFamily.id, preset: scope.id };
                        const added = selectedFeatureKeys.has(featureScopeKey(payload));
                        return (
                          <div key={`${activeFamily.id}-${scope.id}`} className="flex items-center justify-between gap-3 py-3">
                            <div className="min-w-0">
                              <div className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{scope.label}</div>
                              {scope.description ? <div className="mt-1 text-xs leading-5 text-zinc-500 dark:text-zinc-400">{scope.description}</div> : null}
                            </div>
                            <button
                              type="button"
                              disabled={added}
                              className={astroSecondaryButtonCls}
                              onClick={() => addFeatureScope(payload)}
                            >
                              {added ? 'Added' : 'Add'} {scope.label}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {activeFamily?.id === 'positions' && (activeFamily?.scopes || []).some((scope) => scope.custom) ? (
                    <div className="mt-5 border-t border-zinc-100 pt-4 dark:border-zinc-800">
                      <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400">custom range</div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-4">
                        <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-300">
                          Range object
                          <select
                            className={`${astroInputCls} mt-1`}
                            value={rangeDraft.object}
                            onChange={(event) => setRangeDraft((current) => ({ ...current, object: event.target.value }))}
                          >
                            {RESEARCH_OBJECT_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                          </select>
                        </label>
                        <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-300">
                          Range sign
                          <select
                            className={`${astroInputCls} mt-1`}
                            value={rangeDraft.sign}
                            onChange={(event) => setRangeDraft((current) => ({ ...current, sign: event.target.value }))}
                          >
                            {ZODIAC_SIGN_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                          </select>
                        </label>
                        <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-300">
                          Start degree
                          <input
                            className={`${astroInputCls} mt-1`}
                            type="number"
                            min="0"
                            max="30"
                            step="0.1"
                            value={rangeDraft.start_degree}
                            onChange={(event) => setRangeDraft((current) => ({ ...current, start_degree: event.target.value }))}
                          />
                        </label>
                        <label className="text-[11px] font-medium text-zinc-600 dark:text-zinc-300">
                          End degree
                          <input
                            className={`${astroInputCls} mt-1`}
                            type="number"
                            min="0"
                            max="30"
                            step="0.1"
                            value={rangeDraft.end_degree}
                            onChange={(event) => setRangeDraft((current) => ({ ...current, end_degree: event.target.value }))}
                          />
                        </label>
                      </div>
                      <button type="button" className={`${astroPrimaryButtonCls} mt-3`} onClick={addRangeFeature}>
                        Add range
                      </button>
                    </div>
                  ) : null}

                  <div className="mt-5 border-t border-zinc-100 pt-4 dark:border-zinc-800">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400">selected</div>
                        <h5 className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-50">Selected Features</h5>
                      </div>
                      <ConsoleStatusBadge label={`${selectedFeatureScopes.length} total`} tone={selectedFeatureScopes.length ? 'good' : 'default'} />
                    </div>
                    {selectedFeatureScopes.length ? (
                      <div className="mt-3 divide-y divide-zinc-100 border-y border-zinc-100 dark:divide-zinc-800 dark:border-zinc-800">
                        {selectedFeatureScopes.map((scope) => (
                          <div key={featureScopeKey(scope)} className="flex items-center justify-between gap-3 py-2">
                            <span className="min-w-0 text-sm text-zinc-700 dark:text-zinc-200">{featureScopeLabel(activeFamilies, scope)}</span>
                            <button type="button" className={astroSecondaryButtonCls} onClick={() => removeFeatureScope(scope)}>
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-3 border-y border-zinc-100 py-4 text-sm text-zinc-500 dark:border-zinc-800">Add at least one feature before running analysis.</div>
                    )}
                  </div>
                </div>
              </section>

              <section className={astroPanelCls}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <ResearchSectionIntro
                    eyebrow="run"
                    title="Analysis"
                    body="The backend compares this chart set to generated matched charts and ranks recurring signals."
                  />
                  <button
                    type="button"
                    disabled={!rows.length || !selectedFeatureScopes.length || loading}
                    className={astroPrimaryButtonCls}
                    onClick={runAnalysis}
                  >
                    {loading ? <RefreshCw className="mr-2 inline h-3.5 w-3.5 animate-spin" /> : <Play className="mr-2 inline h-3.5 w-3.5" />}
                    Run Analysis
                  </button>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <ResearchStat label="Charts" value={rows.length} />
                  <ResearchStat label="Ready Rows" value={validRowCount} />
                  <ResearchStat label="Scopes" value={selectedFeatureScopes.length} />
                </div>
                {error ? (
                  <div className="mt-4 flex gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                ) : null}
              </section>

              <section className={astroTableFrameCls}>
                <div className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-700">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <ConsoleBracketEyebrow module="default">preview</ConsoleBracketEyebrow>
                      <h3 className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-50">Imported Charts</h3>
                    </div>
                    <ConsoleStatusBadge label={`${rows.length} rows`} />
                  </div>
                </div>
                <div className="max-h-[320px] overflow-auto">
                  {rows.length ? (
                    <table className="min-w-full text-left text-sm">
                      <thead className="sticky top-0 bg-zinc-50 text-[10px] uppercase tracking-[0.16em] text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
                        <tr>
                          <th className="px-4 py-3">Name</th>
                          <th className="px-4 py-3">Date / Time</th>
                          <th className="px-4 py-3">Location</th>
                          <th className="px-4 py-3">Type</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {rows.slice(0, 50).map((row, index) => (
                          <tr key={`${row.name}-${index}`}>
                            <td className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-50">{row.name}</td>
                            <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{row.datetime || `${row.date} ${row.time}`}</td>
                            <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{row.location || `${row.latitude}, ${row.longitude}`}</td>
                            <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{row.chart_type || 'natal'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="px-4 py-10 text-sm text-zinc-500">Import a chart file or load the sample set.</div>
                  )}
                </div>
              </section>

              <section className={astroTableFrameCls}>
                <div className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-700">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <ConsoleBracketEyebrow module="default">results</ConsoleBracketEyebrow>
                      <h3 className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-50">Ranked Signals</h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <ConsoleStatusBadge label={`${manifest.generated_control_count || statistics.control_count || 0} comparison`} />
                      <ConsoleStatusBadge label={`${statistics.signal_count || signals.length || 0} signals`} tone={signals.length ? 'good' : 'default'} />
                    </div>
                  </div>
                </div>
                {signals.length ? (
                  <div className="overflow-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead className="bg-zinc-50 text-[10px] uppercase tracking-[0.16em] text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
                        <tr>
                          <th className="px-4 py-3">Signal</th>
                          <th className="px-4 py-3">Family</th>
                          <th className="px-4 py-3">Target</th>
                          <th className="px-4 py-3">Comparison</th>
                          <th className="px-4 py-3">Lift</th>
                          <th className="px-4 py-3">p</th>
                          <th className="px-4 py-3">q</th>
                          <th className="px-4 py-3">Warnings</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {signals.slice(0, 50).map((signal) => (
                          <tr key={signal.key}>
                            <td className="max-w-[360px] px-4 py-3">
                              <div className="font-medium text-zinc-900 dark:text-zinc-50">{signal.label}</div>
                              <div className="mt-1 text-xs text-zinc-500">{signal.effect_direction === 'less_common' ? 'Less common in chart set' : 'More common in chart set'}</div>
                            </td>
                            <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{String(signal.family || '').replace(/_/g, ' ')}</td>
                            <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{signal.target_count}/{signal.target_total} ({formatPercent(signal.target_rate)})</td>
                            <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{signal.control_count}/{signal.control_total} ({formatPercent(signal.control_rate)})</td>
                            <td className="px-4 py-3 font-mono text-xs text-zinc-600 dark:text-zinc-300">{formatNumber(signal.lift, 2)}</td>
                            <td className="px-4 py-3 font-mono text-xs text-zinc-600 dark:text-zinc-300">{formatNumber(signal.p_value)}</td>
                            <td className="px-4 py-3 font-mono text-xs text-zinc-600 dark:text-zinc-300">{formatNumber(signal.q_value)}</td>
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-1">
                                {(signal.warnings || []).length ? signal.warnings.map((warning) => (
                                  <span key={warning} className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${toneBadgeClass('warning')}`}>
                                    {warningLabel(warning)}
                                  </span>
                                )) : <span className="text-xs text-zinc-400">-</span>}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="px-4 py-10 text-sm text-zinc-500">
                    {result ? 'No ranked signals were returned for this run.' : 'Run analysis to populate ranked signals.'}
                  </div>
                )}
              </section>
            </main>
          </div>
      </div>
    </div>
  );
}
