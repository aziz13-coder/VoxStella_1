import React from 'react';
import { AstroClockAPI } from './api.mjs';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };
const POINTS_HOUSE_SYSTEM = 'P';

function formatNumber(value, digits = 2, fallback = '-') {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : fallback;
}

function isDangerPoint(point) {
  return String(point?.ui_severity || '').toLowerCase() === 'danger'
    || String(point?.ui_color || '').toLowerCase() === 'red';
}

function HitBadge({ type }) {
  const map = { planet: 'planet', angle: 'angle', cusp: 'cusp', part: 'lot' };
  const label = map[type] || type || 'hit';
  return (
    <span
      className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-500"
      style={monoStyle}
    >
      {label}
    </span>
  );
}

function PointDetailRow({ point }) {
  const hits = Array.isArray(point?.hits) ? point.hits.slice(0, 2) : [];
  const primaryHit = hits[0] || null;
  const danger = isDangerPoint(point);
  const rowTone = danger
    ? 'border-red-200 bg-red-50/40'
    : 'border-zinc-100 bg-white';
  const pillTone = danger
    ? 'border-red-200 bg-red-50 text-red-700'
    : point?.ui_severity === 'supportive'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : 'border-zinc-200 bg-white text-zinc-600';

  return (
    <div data-testid="degree-hit-point-row" className={`border-t px-0 py-3 ${rowTone}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-zinc-950">{point?.name || 'Point'}</div>
          <div className="mt-1 text-[12px] text-zinc-500">
            {point?.zodiac?.formatted || 'Degree unavailable'}
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2 text-[10px]" style={monoStyle}>
          <span className={`rounded-full border px-2 py-1 uppercase tracking-[0.14em] ${pillTone}`}>
            {danger ? 'active' : (point?.ui_severity || 'active')}
          </span>
          <span className="rounded-full border border-zinc-200 bg-white px-2 py-1 uppercase tracking-[0.14em] text-zinc-600">
            score {formatNumber(point?.point_score, 3)}
          </span>
        </div>
      </div>
      {primaryHit ? (
        <div className="mt-2 grid gap-1 text-[12px] text-zinc-600">
          {hits.map((hit, index) => (
            <div key={index} className="flex flex-wrap items-center justify-between gap-3">
              <span className="font-medium text-zinc-800">
                {hit.object_name || hit.object || 'Object'} {String(hit.aspect || 'hit').toLowerCase()}
              </span>
              <span className="text-zinc-500" style={monoStyle}>
                orb {formatNumber(hit.orb)} / {formatNumber(hit.allowed_orb)} - strength {formatNumber(hit.strength, 3)}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function DegreeHitsTile({
  metrics,
  specialDegrees,
  onApplyDegrees,
  onClearDegrees,
  pointsContext,
  detailsLocked = false,
  detailsLockedTitle,
  onDetailsLocked,
}) {
  const items = (metrics?.degree_hits?.items || []).slice(0, 6);
  const [input, setInput] = React.useState(() => (
    Array.isArray(specialDegrees) && specialDegrees.length ? specialDegrees.join(', ') : ''
  ));
  const [detailsOpen, setDetailsOpen] = React.useState(false);
  const [pointsLoading, setPointsLoading] = React.useState(false);
  const [pointsError, setPointsError] = React.useState('');
  const [pointsData, setPointsData] = React.useState(null);
  const contextKey = JSON.stringify(pointsContext || {});

  React.useEffect(() => {
    setInput(Array.isArray(specialDegrees) && specialDegrees.length ? specialDegrees.join(', ') : '');
  }, [Array.isArray(specialDegrees) ? specialDegrees.join('|') : '']);

  React.useEffect(() => {
    setPointsData(null);
    setPointsError('');
  }, [contextKey]);

  const topHits = Array.isArray(pointsData?.top_hits) ? pointsData.top_hits.slice(0, 10) : [];

  const loadPointDetails = React.useCallback(async () => {
    setPointsLoading(true);
    setPointsError('');
    setPointsData(null);
    try {
      const response = await AstroClockAPI.getDegreeHitPoints({
        ...(pointsContext || {}),
        houseSystem: POINTS_HOUSE_SYSTEM,
      });
      if (!response?.success) {
        throw new Error(response?.error || response?.detail || 'Unable to load Degree Hits.');
      }
      setPointsData(response.data || {});
    } catch (err) {
      setPointsError(String(err?.message || 'Unable to load Degree Hits.'));
    } finally {
      setPointsLoading(false);
    }
  }, [contextKey]);

  const openDetails = () => {
    if (detailsLocked) {
      onDetailsLocked?.();
      return;
    }
    setDetailsOpen(true);
    if (!pointsLoading) {
      void loadPointDetails();
    }
  };

  const moreButtonCls = detailsLocked
    ? 'rounded-full border border-red-600 bg-red-600 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white hover:border-red-700 hover:bg-red-700'
    : 'rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:border-zinc-300';

  return (
    <div className={`${panelCls} min-h-[280px] flex flex-col`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
            Degree Analysis
          </div>
          <h3 className="mt-1 font-semibold text-sm">Degree Hits</h3>
        </div>
        <div className="flex flex-col items-end gap-2">
          <button
            type="button"
            onClick={openDetails}
            className={moreButtonCls}
            style={monoStyle}
            title={detailsLocked ? detailsLockedTitle : undefined}
          >
            More
          </button>
        </div>
      </div>

      <div className="mt-3 border-t border-zinc-100 pt-3">
        <div className="grid gap-2">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="e.g., 25 59 Leo, Leo 21 15"
              className="w-full rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-[12px] text-zinc-700 focus:outline-none focus:ring-1 focus:ring-zinc-300"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              className="rounded-full border border-zinc-900 bg-zinc-900 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white"
              style={monoStyle}
              onClick={() => {
                const tokens = (input || '')
                  .split(',')
                  .map((segment) => segment.trim())
                  .filter(Boolean);
                onApplyDegrees?.(tokens);
              }}
            >
              Apply
            </button>
            <button
              className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500"
              style={monoStyle}
              onClick={() => {
                setInput('');
                onClearDegrees?.();
              }}
            >
              Clear
            </button>
          </div>
          <div className="text-[11px] leading-4 text-zinc-500">
            Accepts sign-first or sign-last degrees, with optional minutes.
          </div>
        </div>
      </div>

      <div data-testid="degree-hits-results" className="mt-3 min-h-[88px] flex-1 overflow-auto pr-1">
        {items.length === 0 ? (
          <div className="text-sm leading-5 text-zinc-500">
            <div>No applied special degree hits yet.</div>
            <div>Add one above to check the current degree stack.</div>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="border-t border-zinc-100 pt-2.5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-[1rem] leading-tight text-zinc-900" style={serifStyle}>
                      {item.degree}
                    </div>
                    <div className="mt-1 text-[11px] text-zinc-500">
                      stack {item.stack_factor} - {item.count} hit{Number(item.count) === 1 ? '' : 's'}
                    </div>
                  </div>
                  <div className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
                    {item.midpoint_active ? 'midpoint' : 'direct'}
                  </div>
                </div>
                {Array.isArray(item.hits) && item.hits.length ? (
                  <div className="mt-2 space-y-1.5">
                    {item.hits.slice(0, 6).map((hit, hitIndex) => (
                      <div key={hitIndex} className="flex items-center justify-between gap-3 text-[11px]">
                        <div className="min-w-0 truncate text-zinc-700">
                          <HitBadge type={hit.type} />
                          <span className="ml-1 truncate">{hit.target}</span>
                        </div>
                        <div className="shrink-0 text-zinc-500">
                          {hit.orb != null ? `${Number(hit.orb).toFixed(2)} deg` : '-'}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      {detailsOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/30 px-4 py-6">
          <div
            role="dialog"
            aria-label="Degree Hits Details"
            className="max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-xl"
          >
            <div className="flex items-start justify-between gap-4 border-b border-zinc-100 px-5 py-4">
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
                  Degree Hits
                </div>
                <h3 className="mt-1 text-base font-semibold text-zinc-950">Degree Hits Details</h3>
                <div className="mt-1 text-[12px] text-zinc-500">Top 10 active symbolic points</div>
              </div>
              <button
                type="button"
                onClick={() => setDetailsOpen(false)}
                className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 hover:border-zinc-300"
                style={monoStyle}
              >
                Close
              </button>
            </div>

            <div className="max-h-[calc(88vh-92px)] overflow-auto px-5 py-4">
              {pointsLoading ? (
                <div className="py-8 text-sm text-zinc-500">Loading Degree Hits...</div>
              ) : pointsError ? (
                <div className="py-6">
                  <div className="border-y border-red-100 bg-red-50/70 px-3 py-4 text-sm text-red-700">
                    {pointsError}
                  </div>
                  <button
                    type="button"
                    onClick={loadPointDetails}
                    className="mt-3 rounded-full border border-zinc-900 bg-zinc-900 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white"
                    style={monoStyle}
                  >
                    Retry
                  </button>
                </div>
              ) : topHits.length ? (
                <div>
                  {topHits.map((point) => (
                    <PointDetailRow key={point.key || `${point.name}-${point.longitude}`} point={point} />
                  ))}
                </div>
              ) : (
                <div className="py-8 text-sm text-zinc-500">No active symbolic point hits were returned.</div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
