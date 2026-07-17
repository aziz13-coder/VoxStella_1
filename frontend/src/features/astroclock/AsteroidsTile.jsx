import React from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };

function formatDegreeInSign(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const degrees = Math.floor(numeric);
  const minutes = Math.floor((numeric - degrees) * 60);
  return `${degrees}°${String(minutes).padStart(2, '0')}'`;
}

function formatSpeed(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return numeric.toFixed(3);
}

function formatAzimuth(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `${numeric.toFixed(1)}°`;
}

export default function AsteroidsTile({ asteroids }) {
  const items = Array.isArray(asteroids?.items) ? asteroids.items : [];
  const missing = Array.isArray(asteroids?.missing) ? asteroids.missing : [];
  const message = typeof asteroids?.message === 'string' ? asteroids.message : null;

  return (
    <div className={`${panelCls} flex flex-col`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
            Minor Bodies
          </div>
          <h3 className="mt-1 font-semibold text-sm">Asteroids</h3>
        </div>
        {items.length ? (
          <div className="rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
            {items.length} tracked
          </div>
        ) : null}
      </div>

      {message && !items.length ? (
        <div className="mt-3 rounded-2xl border border-zinc-200 bg-white px-3 py-2.5 text-[12px] text-zinc-500">
          {message}
        </div>
      ) : null}

      <div className="mt-3 flex-1 overflow-auto pr-1">
        {items.length === 0 ? (
          <div className="text-sm text-zinc-500">No asteroid data available.</div>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item?.name} className="rounded-2xl border border-zinc-100 bg-white px-3 py-2.5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-[15px] leading-5 text-zinc-900" style={serifStyle}>
                      {item?.name || 'Asteroid'}{item?.retrograde ? ' R' : ''}
                    </div>
                    <div className="mt-1 text-[12px] text-zinc-600">
                      {item?.sign || '--'} {formatDegreeInSign(item?.degree_in_sign)}
                      <span className="mx-1 text-zinc-300">·</span>
                      {Number.isFinite(Number(item?.house)) ? `H${Number(item.house)}` : 'H-'}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[1rem] leading-none text-zinc-900" style={serifStyle}>
                      {formatSpeed(item?.speed)}
                    </div>
                    <div className="mt-1 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>
                      speed
                    </div>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
                  <span>{item?.direction_label || '--'}</span>
                  <span>{formatAzimuth(item?.azimuth_deg)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {missing.length ? (
        <div className="mt-3 border-t border-zinc-100 pt-3 text-[11px] text-zinc-500">
          Missing: {missing.map((item) => item?.name).filter(Boolean).join(', ')}
        </div>
      ) : null}
    </div>
  );
}
