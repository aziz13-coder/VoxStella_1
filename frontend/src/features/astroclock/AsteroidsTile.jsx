import React from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';

function formatDegreeInSign(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const degrees = Math.floor(numeric);
  const minutes = Math.floor((numeric - degrees) * 60);
  return `${degrees}\u00B0${String(minutes).padStart(2, '0')}'`;
}

function formatSpeed(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return numeric.toFixed(3);
}

function formatAzimuth(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `${numeric.toFixed(1)} deg`;
}

export default function AsteroidsTile({ asteroids }) {
  const items = Array.isArray(asteroids?.items) ? asteroids.items : [];
  const missing = Array.isArray(asteroids?.missing) ? asteroids.missing : [];
  const message = typeof asteroids?.message === 'string' ? asteroids.message : null;

  return (
    <div className={`${panelCls} flex flex-col`}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h3 className="font-semibold text-sm">Asteroids</h3>
        {items.length ? <div className="text-[11px] text-zinc-500">{items.length} tracked</div> : null}
      </div>
      {message && !items.length ? (
        <div className="mb-3 text-[12px] text-zinc-500">{message}</div>
      ) : null}
      <div className="flex-1 overflow-auto pr-1">
        {items.length === 0 ? (
          <div className="text-sm text-zinc-500">No asteroid data available.</div>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item?.name} className="border-b border-zinc-100 pb-2 last:border-0 last:pb-0">
                <div className="grid grid-cols-12 items-start gap-2">
                  <div className="col-span-3">
                    <div className="font-medium text-sm text-zinc-900">
                      {item?.name || 'Asteroid'}{item?.retrograde ? ' R' : ''}
                    </div>
                  </div>
                  <div className="col-span-4 text-sm text-zinc-800">
                    <div>{item?.sign || '--'} {formatDegreeInSign(item?.degree_in_sign)}</div>
                    <div className="text-[11px] text-zinc-500">
                      {Number.isFinite(Number(item?.house)) ? `House ${Number(item.house)}` : 'House --'}
                    </div>
                  </div>
                  <div className="col-span-3 text-sm text-zinc-800">
                    <div>{item?.direction_label || '--'}</div>
                    <div className="text-[11px] text-zinc-500">{formatAzimuth(item?.azimuth_deg)}</div>
                  </div>
                  <div className="col-span-2 text-right">
                    <div className="text-sm text-zinc-800">{formatSpeed(item?.speed)}</div>
                    <div className="text-[11px] text-zinc-500">speed</div>
                  </div>
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
