import React, { useEffect, useMemo, useState } from 'react';
import { AstroClockAPI } from './api.mjs';

const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };

const PLANET_SYMBOLS = {
  Sun: '☉',
  Moon: '☽',
  Mercury: '☿',
  Venus: '♀',
  Mars: '♂',
  Jupiter: '♃',
  Saturn: '♄',
};

const glyph = (name) => PLANET_SYMBOLS[name] || name || '?';

const typeLabel = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'mutual_rulership') return 'Mutual domicile';
  if (normalized === 'mutual_exaltation') return 'Mutual exaltation';
  if (normalized === 'mutual_term') return 'Mutual term';
  if (normalized === 'mutual_face') return 'Mutual face';
  if (normalized === 'mixed_reception') return 'Mixed reception';
  if (normalized === 'unilateral') return 'Unilateral reception';
  if (normalized === 'none') return 'No reception';
  return value || 'Reception';
};

const typeAbbrev = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'mutual_rulership') return 'D';
  if (normalized === 'mutual_exaltation') return 'Ex';
  if (normalized === 'mutual_term') return 'T';
  if (normalized === 'mutual_face') return 'F';
  if (normalized === 'mixed_reception') return 'Mix';
  return 'Rec';
};

const dignityAbbrev = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'domicile' || normalized === 'rulership' || normalized === 'ruler') return 'R';
  if (normalized === 'exaltation' || normalized === 'exalted') return 'Ex';
  if (normalized === 'triplicity') return 'Tri';
  if (normalized === 'term' || normalized === 'bounds' || normalized === 'bound') return 'T';
  if (normalized === 'face' || normalized === 'decan' || normalized === 'decanate') return 'F';
  return value || '?';
};

const dignityTitle = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'domicile' || normalized === 'rulership' || normalized === 'ruler') return 'Domicile / Rulership';
  if (normalized === 'exaltation' || normalized === 'exalted') return 'Exaltation';
  if (normalized === 'triplicity') return 'Triplicity';
  if (normalized === 'term' || normalized === 'bounds' || normalized === 'bound') return 'Term / Bounds';
  if (normalized === 'face' || normalized === 'decan' || normalized === 'decanate') return 'Face / Decan';
  return value || '';
};

function formatTraditional(value) {
  if (!value) return null;
  try {
    if (typeof value === 'string') return typeLabel(value);
    if (typeof value === 'object') {
      if (value.display_text) return String(value.display_text);
      if (value.type) return typeLabel(value.type);
    }
  } catch (_) {}
  return String(value);
}

function strengthChip(value) {
  return (
    <span
      className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-500"
      style={monoStyle}
    >
      S{value ?? 0}
    </span>
  );
}

function emptyState(label) {
  return <div className="text-[11px] text-zinc-500">{label}</div>;
}

export default function ReceptionsTile({ dataTimestamp, receptions = null, clockContext = null }) {
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const clockContextKey = useMemo(() => {
    try {
      return JSON.stringify(clockContext || {});
    } catch (_) {
      return '';
    }
  }, [clockContext]);

  useEffect(() => {
    let alive = true;
    if (receptions && typeof receptions === 'object') {
      setRec(receptions);
      setError(null);
      setLoading(false);
      return () => {
        alive = false;
      };
    }
    setLoading(true);
    setError(null);
    AstroClockAPI.getReceptions(clockContext || {})
      .then((res) => {
        if (!alive) return;
        if (res?.success) setRec(res.data || {});
      })
      .catch((err) => {
        if (!alive) return;
        const message = String(err?.message || '');
        if (message.includes('license_required') || message.includes('license_invalid')) {
          setError('License required');
          return;
        }
        setError('Failed to load');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [dataTimestamp, receptions, clockContextKey]);

  if (loading && !rec) return <div className="text-sm text-zinc-500">Loading...</div>;
  if (error) return <div className="text-sm text-red-600">{error}</div>;

  const mutual = Array.isArray(rec?.mutual) ? rec.mutual : [];
  const unilateral = Array.isArray(rec?.top_unilateral) ? rec.top_unilateral : [];

  const summary = (() => {
    const raw = rec?.traditional_reception;
    if (raw && typeof raw === 'object') {
      return {
        type: String(raw.type || 'none'),
        displayText: formatTraditional(raw) || 'No reception',
        mutualCount: Number(raw.mutual_count || mutual.length || 0),
        unilateralCount: Number(raw.unilateral_count || unilateral.length || 0),
      };
    }
    if (mutual.length > 0) {
      const type = String(mutual[0]?.type || 'mixed_reception');
      return {
        type,
        displayText: typeLabel(type),
        mutualCount: mutual.length,
        unilateralCount: unilateral.length,
      };
    }
    if (unilateral.length > 0) {
      return {
        type: 'unilateral',
        displayText: 'Unilateral reception',
        mutualCount: 0,
        unilateralCount: unilateral.length,
      };
    }
    return {
      type: 'none',
      displayText: 'No reception',
      mutualCount: 0,
      unilateralCount: 0,
    };
  })();

  return (
    <div className="space-y-3 text-sm">
      <div className="border-b border-zinc-100 pb-3">
        <div className="text-[1rem] leading-tight text-zinc-900" style={serifStyle}>
          {summary.displayText}
        </div>
        <div className="mt-1 text-[11px] text-zinc-500">
          {summary.mutualCount} mutual · {summary.unilateralCount} unilateral
        </div>
      </div>

      <div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
          Mutual
        </div>
        <div className="mt-2 space-y-2">
          {mutual.length === 0
            ? emptyState('No mutual receptions.')
            : mutual.map((item, index) => (
              <div
                key={`mutual-${index}`}
                className="border-t border-zinc-100 pt-2.5"
                title={`${item.p1} ↔ ${item.p2} · ${typeLabel(item.type)}`}
              >
                <div className="flex items-center gap-2">
                  <div className="text-[14px] leading-none text-zinc-900">
                    {glyph(item.p1)} ↔ {glyph(item.p2)}
                  </div>
                  <div className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
                    {typeAbbrev(item.type)}
                  </div>
                  <div className="ml-auto">{strengthChip(item.strength)}</div>
                </div>
                <div className="mt-1 text-[11px] text-zinc-500">{typeLabel(item.type)}</div>
              </div>
            ))}
        </div>
      </div>

      <div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
          Unilateral
        </div>
        <div className="mt-2 space-y-2">
          {unilateral.length === 0
            ? emptyState('No unilateral receptions.')
            : unilateral.map((item, index) => (
              <div
                key={`unilateral-${index}`}
                className="border-t border-zinc-100 pt-2.5"
                title={`${item.receiving} receives ${item.received}`}
              >
                <div className="flex items-center gap-2">
                  <div className="text-[14px] leading-none text-zinc-900">
                    {glyph(item.received)} → {glyph(item.receiving)}
                  </div>
                  <div className="ml-auto">{strengthChip(item.strength)}</div>
                </div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  {item.receiving} receives {item.received}
                </div>
                {Array.isArray(item.dignities) && item.dignities.length ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {item.dignities.map((dignity, dignityIndex) => (
                      <span
                        key={`${index}-d-${dignityIndex}`}
                        className="rounded-full border border-zinc-200 bg-white px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-500"
                        style={monoStyle}
                        title={dignityTitle(dignity)}
                      >
                        {dignityAbbrev(dignity)}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
