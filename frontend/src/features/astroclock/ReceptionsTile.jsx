import React, { useEffect, useState } from 'react';
import { AstroClockAPI } from './api.mjs';

const PlanetSymbols = {
  Sun: '☉',
  Moon: '☾',
  Mercury: '☿',
  Venus: '♀',
  Mars: '♂',
  Jupiter: '♃',
  Saturn: '♄',
};

const glyph = (name) => PlanetSymbols[name] || name || '?';

const typeLabel = (t) => {
  const m = String(t || '').toLowerCase();
  if (m === 'mutual_rulership') return 'Mutual domicile';
  if (m === 'mutual_exaltation') return 'Mutual exaltation';
  if (m === 'mutual_term') return 'Mutual term';
  if (m === 'mutual_face') return 'Mutual face';
  if (m === 'mixed_reception') return 'Mixed reception';
  return t || '—';
};

const typeAbbrev = (t) => {
  const m = String(t || '').toLowerCase();
  if (m === 'mutual_rulership') return 'D';
  if (m === 'mutual_exaltation') return 'Ex';
  if (m === 'mutual_term') return 'T';
  if (m === 'mutual_face') return 'F';
  if (m === 'mixed_reception') return 'Mix';
  return 'Rec';
};

const dignityAbbrev = (d) => {
  const m = String(d || '').toLowerCase();
  if (m === 'domicile' || m === 'rulership' || m === 'ruler') return 'R';
  if (m === 'exaltation' || m === 'exalted') return 'Ex';
  if (m === 'triplicity') return 'Tri';
  if (m === 'term' || m === 'bounds' || m === 'bound') return 'T';
  if (m === 'face' || m === 'decan' || m === 'decanate') return 'F';
  return d || '?';
};

const dignityTitle = (d) => {
  const m = String(d || '').toLowerCase();
  if (m === 'domicile' || m === 'rulership' || m === 'ruler') return 'Domicile / Rulership';
  if (m === 'exaltation' || m === 'exalted') return 'Exaltation';
  if (m === 'triplicity') return 'Triplicity';
  if (m === 'term' || m === 'bounds' || m === 'bound') return 'Term / Bounds';
  if (m === 'face' || m === 'decan' || m === 'decanate') return 'Face / Decan';
  return d || '';
};

export default function ReceptionsTile({ dataTimestamp, receptions = null }) {
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const formatTraditional = (val) => {
    if (!val) return null;
    try {
      if (typeof val === 'string') {
        const m = val.toLowerCase();
        if (m === 'mutual_rulership') return 'Mutual domicile reception';
        if (m === 'mutual_exaltation') return 'Mutual exaltation reception';
        if (m === 'mixed_reception') return 'Mixed reception';
        if (m === 'unilateral') return 'Unilateral reception';
        if (m === 'none') return 'No reception';
        return val;
      }
      if (typeof val === 'object') {
        if (val.display_text) return String(val.display_text);
        if (val.type) return typeLabel(val.type);
        return JSON.stringify(val);
      }
    } catch (_) {}
    return String(val);
  };

  useEffect(() => {
    let alive = true;
    if (receptions && typeof receptions === 'object') {
      setRec(receptions);
      setError(null);
      setLoading(false);
      return () => { alive = false; };
    }
    setLoading(true);
    setError(null);
    AstroClockAPI.getReceptions()
      .then((res) => {
        if (!alive) return;
        if (res?.success) setRec(res.data || {});
      })
      .catch((err) => {
        if (!alive) return;
        const msg = String(err?.message || '');
        if (msg.includes('license_required') || msg.includes('license_invalid')) {
          setError('License required');
          return;
        }
        setError('Failed to load');
      })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [dataTimestamp, receptions]);

  if (loading && !rec) return <div className="text-sm text-zinc-500">Loading…</div>;
  if (error) return <div className="text-sm text-red-600">{error}</div>;

  const mutual = Array.isArray(rec?.mutual) ? rec.mutual : [];
  const unilateral = Array.isArray(rec?.top_unilateral) ? rec.top_unilateral : [];
  const summary = (() => {
    const raw = rec?.traditional_reception;
    if (raw && typeof raw === 'object') {
      const type = String(raw.type || 'none');
      const displayText = formatTraditional(raw);
      return {
        type,
        displayText: displayText || 'No reception',
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
        mutualCount: mutual.length,
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

  const badge = (txt) => (
    <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 text-xs bg-white" key={txt}>{txt}</span>
  );

  return (
    <div className="text-sm space-y-3">
      <div>
        <div className="font-medium mb-0.5">
          <div className="font-medium">Traditional</div>
        </div>
        <div className="text-xs text-zinc-700">{summary.displayText}</div>
        {(summary.mutualCount > 0 || summary.unilateralCount > 0) ? (
          <div className="text-[11px] text-zinc-500">
            {summary.mutualCount} mutual · {summary.unilateralCount} unilateral
          </div>
        ) : null}
      </div>

      <div>
        <div className="font-medium mb-1">Mutual Receptions</div>
        {mutual.length === 0 ? (
          <div className="text-xs text-zinc-500">None</div>
        ) : (
          <ul className="space-y-1">
            {mutual.map((m, i) => (
              <li
                key={i}
                className="text-xs flex items-center gap-2"
                title={`${m.p1} ↔ ${m.p2} · ${typeLabel(m.type)} · Strength ${m.strength ?? 0}`}
              >
                <span className="inline-flex items-center gap-1">
                  <span className="text-base leading-none">{glyph(m.p1)}</span>
                  <span className="mx-0.5">↔</span>
                  <span className="text-base leading-none">{glyph(m.p2)}</span>
                </span>
                <span className="px-1.5 py-0.5 rounded-full border border-zinc-200 bg-white text-[10px]" title={typeLabel(m.type)}>
                  {typeAbbrev(m.type)}
                </span>
                <span className="ml-auto">{badge(`S${m.strength ?? 0}`)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <div className="font-medium mb-1">Unilateral Receptions</div>
        {unilateral.length === 0 ? (
          <div className="text-xs text-zinc-500">None</div>
        ) : (
          <ul className="space-y-1">
            {unilateral.map((u, i) => (
              <li
                key={i}
                className="text-xs flex items-center gap-2"
                title={`${u.receiving} receives ${u.received} · by ${Array.isArray(u.dignities) ? u.dignities.join(', ') : ''} · Strength ${u.strength ?? 0}`}
              >
                <span className="inline-flex items-center gap-1">
                  <span className="text-base leading-none">{glyph(u.received)}</span>
                  <span className="mx-0.5">→</span>
                  <span className="text-base leading-none">{glyph(u.receiving)}</span>
                </span>
                {Array.isArray(u.dignities) && u.dignities.length ? (
                  <span className="inline-flex items-center gap-1 ml-1">
                    {u.dignities.map((d, idx) => (
                      <span
                        key={`${i}-d-${idx}`}
                        className="px-1 py-0.5 rounded-full border border-zinc-200 bg-white text-[10px]"
                        title={dignityTitle(d)}
                      >
                        {dignityAbbrev(d)}
                      </span>
                    ))}
                  </span>
                ) : null}
                <span className="ml-auto">{badge(`S${u.strength ?? 0}`)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
