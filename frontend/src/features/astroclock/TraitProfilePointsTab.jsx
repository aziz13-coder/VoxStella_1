import React from 'react';
import { AstroClockAPI } from './api.mjs';

const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const POINTS_HOUSE_SYSTEM = 'P';
const SEX_OPTIONS = [
  { value: '0', label: 'Unspecified' },
  { value: '1', label: 'Male' },
  { value: '2', label: 'Female' },
];

function Micro({ children, className = '' }) {
  return (
    <span className={`font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-500 ${className}`}>
      {children}
    </span>
  );
}

function Pill({ children, active = false, tone = 'default', className = '' }) {
  const toneCls = (() => {
    if (active) return 'border-zinc-950 bg-zinc-950 text-white';
    if (tone === 'danger') return 'border-red-200 bg-red-50 text-red-700';
    if (tone === 'positive') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
    if (tone === 'muted') return 'border-zinc-200 bg-zinc-100 text-zinc-700';
    return 'border-zinc-200 bg-white text-zinc-700';
  })();
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] leading-none ${toneCls} ${className}`}>
      {children}
    </span>
  );
}

function formatNumber(value, digits = 2, fallback = '-') {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : fallback;
}

function pointScoreLabel(score) {
  const value = Number(score);
  if (!Number.isFinite(value) || value <= 0) return 'inactive';
  if (value < 0.5) return 'weak hit';
  if (value < 1) return 'active hit';
  return 'strong hit';
}

function pointTone(point) {
  if (String(point?.ui_severity || '').toLowerCase() === 'danger' || String(point?.ui_color || '').toLowerCase() === 'red') {
    return 'danger';
  }
  const value = Number(point?.score ?? point?.point_score);
  if (!Number.isFinite(value) || value <= 0) return 'muted';
  if (value < 1) return 'default';
  return 'positive';
}

function pointBarClass(tone) {
  if (tone === 'danger') return 'bg-red-600';
  if (tone === 'positive') return 'bg-emerald-600';
  if (tone === 'muted') return 'bg-zinc-300';
  return 'bg-zinc-950';
}

function strengthPercent(score) {
  const value = Number(score);
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.max(6, Math.min(100, Math.round(value * 42)));
}

function PointHitRow({ hit }) {
  if (!hit) return null;
  const aspect = String(hit.aspect || 'Hit').toLowerCase();
  const objectName = hit.object_name || hit.object || 'object';
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-zinc-100 py-2 text-[11px] text-zinc-600">
      <span className="font-medium text-zinc-800">{aspect} {objectName}</span>
      <span className="text-zinc-500" style={monoStyle}>
        orb {formatNumber(hit.orb)} / {formatNumber(hit.allowed_orb)} - strength {formatNumber(hit.strength, 3)}
      </span>
    </div>
  );
}

function PointRow({ point }) {
  const hits = Array.isArray(point?.hits) ? point.hits : [];
  const active = hits.length > 0;
  const tone = pointTone(point);
  const score = point?.score ?? point?.point_score;
  return (
    <div data-testid="trait-point-row" className="py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-zinc-950">{point?.name || 'Point'}</div>
          <div className="mt-1 text-[12px] text-zinc-500">
            {point?.zodiac?.formatted ? `Degree: ${point.zodiac.formatted}` : 'Degree not computed'}
          </div>
        </div>
        <Pill tone={tone} className="font-mono uppercase tracking-[0.08em]">
          {pointScoreLabel(score)}
        </Pill>
      </div>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
        <div
          className={`h-full rounded-full ${pointBarClass(tone)}`}
          style={{ width: `${strengthPercent(score)}%` }}
        />
      </div>
      {active ? (
        <div className="mt-2">
          {hits.map((hit, index) => <PointHitRow key={index} hit={hit} />)}
        </div>
      ) : (
        <div className="mt-2 text-[12px] leading-5 text-zinc-500">
          No active point hit in the configured aspect matrix.
        </div>
      )}
    </div>
  );
}

export default function TraitProfilePointsTab({ chartContext }) {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');
  const [data, setData] = React.useState(null);
  const [sexCode, setSexCode] = React.useState('0');
  const contextKey = JSON.stringify({ chartContext: chartContext || {}, sexCode });

  const loadPoints = React.useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await AstroClockAPI.getDegreeHitPoints({
        ...(chartContext || {}),
        houseSystem: POINTS_HOUSE_SYSTEM,
        sexCode,
      });
      if (!response?.success) {
        throw new Error(response?.error || response?.detail || 'Unable to load active points.');
      }
      setData(response.data || null);
    } catch (err) {
      setError(String(err?.message || 'Unable to load active points.'));
    } finally {
      setLoading(false);
    }
  }, [contextKey]);

  React.useEffect(() => {
    setData(null);
    void loadPoints();
  }, [loadPoints]);

  const points = Array.isArray(data?.top_hits) ? data.top_hits : (Array.isArray(data?.points) ? data.points : []);
  const activePoints = points
    .filter((point) => point?.available !== false)
    .filter((point) => Array.isArray(point?.hits) && point.hits.length)
    .sort((a, b) => {
      const scoreDelta = Number(b?.point_score ?? b?.score ?? 0) - Number(a?.point_score ?? a?.score ?? 0);
      if (scoreDelta) return scoreDelta;
      const aStrongest = Array.isArray(a?.hits) ? Math.max(0, ...a.hits.map((hit) => Number(hit?.strength || 0))) : 0;
      const bStrongest = Array.isArray(b?.hits) ? Math.max(0, ...b.hits.map((hit) => Number(hit?.strength || 0))) : 0;
      if (bStrongest !== aStrongest) return bStrongest - aStrongest;
      return String(a?.name || '').localeCompare(String(b?.name || ''));
    });
  const displayPoints = activePoints.slice(0, 10);
  const totalActiveCount = Number.isFinite(Number(data?.active_count)) ? Number(data.active_count) : activePoints.length;
  const countLabel = loading
    ? 'loading'
    : `${displayPoints.length} shown${totalActiveCount > displayPoints.length ? ` / ${totalActiveCount} active` : ''}`;

  return (
    <div className="p-7">
      <div className="mx-auto max-w-5xl">
        <div className="mb-4 flex flex-col gap-3 border-b border-zinc-200 pb-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Micro className="block">symbolic points</Micro>
            <h3 className="mt-1 font-serif text-[26px] leading-tight text-zinc-950">Active Points</h3>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <Micro>{countLabel}</Micro>
            <div className="flex items-center gap-2">
              <Micro>Subject sex</Micro>
              <div role="group" aria-label="Subject sex" className="flex overflow-hidden rounded-full border border-zinc-200 bg-white">
                {SEX_OPTIONS.map((option) => {
                  const selected = sexCode === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSexCode(option.value)}
                      className={`px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] ${
                        selected
                          ? 'bg-zinc-950 text-white'
                          : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-950'
                      }`}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="mt-5 border-y border-zinc-100 py-10 text-sm text-zinc-500">Loading active points...</div>
        ) : error ? (
          <div className="mt-5 border-y border-rose-100 bg-rose-50/60 px-4 py-6">
            <div className="text-sm text-red-600">{error}</div>
            <button
              type="button"
              onClick={loadPoints}
              className="mt-3 rounded-full border border-zinc-900 bg-zinc-900 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white"
              style={monoStyle}
            >
              Retry
            </button>
          </div>
        ) : (
          <section>
            <div className="divide-y divide-zinc-100">
              {displayPoints.length ? (
                displayPoints.map((point) => <PointRow key={point.key} point={point} />)
              ) : (
                <div className="border-y border-zinc-100 py-6 text-sm text-zinc-500">
                  No active points were returned.
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
