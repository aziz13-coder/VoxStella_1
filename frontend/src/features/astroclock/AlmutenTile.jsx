import React from 'react';

const panelCls = 'rounded-2xl border border-zinc-200 bg-white shadow-sm p-4';
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };

const DIGNITY_LABELS = {
  domicile: 'Domicile',
  exaltation: 'Exaltation',
  triplicity: 'Triplicity',
  term: 'Term',
  face: 'Face',
};

const BREAKDOWN_ORDER = ['domicile', 'exaltation', 'triplicity', 'term', 'face'];
const POINT_LABEL_ALIASES = {
  Ascendant: 'Asc',
  Midheaven: 'Mid',
};
const ZODIAC_SIGNS = [
  'Aries',
  'Taurus',
  'Gemini',
  'Cancer',
  'Leo',
  'Virgo',
  'Libra',
  'Scorpio',
  'Sagittarius',
  'Capricorn',
  'Aquarius',
  'Pisces',
];
const DEFAULT_METHOD_LABEL = 'Lilly · sect ruler';
const METHOD_LABELS = {
  lilly_sect: DEFAULT_METHOD_LABEL,
  traditional_essential_dignity_almuten_v2: 'Egyptian terms · sect-ruler triplicity',
};

function formatZodiacPosition(sign, value) {
  const numeric = Number(value);
  const rawSign = String(sign || '').trim();
  if (!Number.isFinite(numeric)) return `${rawSign || '--'} --`;

  const roundedMinutes = Math.round(numeric * 60);
  const minutesPerSign = 30 * 60;
  const signIndex = ZODIAC_SIGNS.indexOf(rawSign);

  if (signIndex >= 0) {
    const signCarry = Math.floor(roundedMinutes / minutesPerSign);
    const normalizedMinutes = roundedMinutes - (signCarry * minutesPerSign);
    const normalizedSignIndex = ((signIndex + signCarry) % ZODIAC_SIGNS.length + ZODIAC_SIGNS.length) % ZODIAC_SIGNS.length;
    const degrees = Math.floor(normalizedMinutes / 60);
    const minutes = normalizedMinutes % 60;
    return `${ZODIAC_SIGNS[normalizedSignIndex]} ${degrees}\u00B0${String(minutes).padStart(2, '0')}'`;
  }

  const degrees = Math.floor(roundedMinutes / 60);
  const minutes = Math.abs(roundedMinutes - (degrees * 60));
  return `${rawSign || '--'} ${degrees}\u00B0${String(minutes).padStart(2, '0')}'`;
}

function formatPointLabel(value) {
  const label = String(value || '').trim();
  if (!label) return 'Point';
  return POINT_LABEL_ALIASES[label] || label;
}

function formatBreakdownChips(breakdown) {
  if (!breakdown || typeof breakdown !== 'object') return [];
  return BREAKDOWN_ORDER
    .filter((key) => Number(breakdown[key]) > 0)
    .map((key) => `${DIGNITY_LABELS[key] || key} +${Number(breakdown[key])}`);
}

function resolveMethodLabel(almutens) {
  const method = almutens?.method;
  if (method && typeof method === 'object') {
    const label = String(method.label || '').trim();
    if (label) return label;
    const knownLabel = METHOD_LABELS[String(method.id || '').trim()];
    if (knownLabel) return knownLabel;
  } else if (typeof method === 'string') {
    const knownLabel = METHOD_LABELS[method.trim()];
    if (knownLabel) return knownLabel;
  }

  const doctrine = almutens?.doctrine;
  if (doctrine && typeof doctrine === 'object') {
    const terms = String(doctrine.terms || '').trim().toLowerCase();
    const triplicity = String(doctrine.triplicity || '').trim().toLowerCase();
    const termsLabel = terms === 'egyptian' ? 'Egyptian terms' : null;
    const triplicityLabel = triplicity === 'dorothean_sect_ruler_only' ? 'sect-ruler triplicity' : null;
    if (termsLabel && triplicityLabel) return `${termsLabel} · ${triplicityLabel}`;
    if (termsLabel) return termsLabel;
    if (triplicityLabel) return triplicityLabel;
  }

  return DEFAULT_METHOD_LABEL;
}

function resolveCalculationNote(almutens) {
  const withheldDignities = Array.isArray(almutens?.withheld_dignities)
    ? almutens.withheld_dignities.map((name) => String(name || '').trim().toLowerCase())
    : [];
  if (withheldDignities.includes('triplicity')) {
    return 'Sect unavailable · triplicity not scored';
  }
  if (String(almutens?.calculation_status || '').trim().toLowerCase() === 'partial') {
    return 'Partial calculation · some dignities not scored';
  }
  return null;
}

function getLeaderDetails(item) {
  const explicitDetails = Array.isArray(item?.leader_details)
    ? item.leader_details.filter((detail) => detail && typeof detail === 'object' && String(detail.planet || '').trim())
    : [];
  if (explicitDetails.length) return explicitDetails;

  const declaredLeaders = Array.isArray(item?.leaders)
    ? item.leaders
    : [];
  const fallbackLeaders = [
    item?.leader,
    ...(Array.isArray(item?.tied_with) ? item.tied_with : []),
  ];
  const leaderNames = [...new Set((declaredLeaders.length ? declaredLeaders : fallbackLeaders)
    .map((name) => String(name || '').trim())
    .filter(Boolean))];
  const candidates = Array.isArray(item?.candidates) ? item.candidates : [];

  return leaderNames.map((planet, index) => {
    const candidate = candidates.find((row) => String(row?.planet || '').trim() === planet);
    const isPrimaryLeader = planet === String(item?.leader || '').trim() || (!item?.leader && index === 0);
    return {
      planet,
      score: candidate?.score ?? item?.leader_score,
      dignities: Array.isArray(candidate?.dignities)
        ? candidate.dignities
        : (isPrimaryLeader && Array.isArray(item?.leader_dignities) ? item.leader_dignities : []),
      breakdown: candidate?.breakdown && typeof candidate.breakdown === 'object'
        ? candidate.breakdown
        : (isPrimaryLeader ? item?.leader_breakdown : {}),
    };
  });
}

function formatLeaderLabel(leaderDetails) {
  const leaders = leaderDetails.map((detail) => detail.planet).filter(Boolean);
  return leaders.length ? leaders.join(' / ') : 'No leader';
}

export default function AlmutenTile({ almutens }) {
  const items = Array.isArray(almutens?.items) ? almutens.items : [];
  const sect = typeof almutens?.sect === 'string' ? almutens.sect : null;
  const methodLabel = resolveMethodLabel(almutens);
  const calculationNote = resolveCalculationNote(almutens);
  const ascItem = items.find((item) => String(item?.label || '').toLowerCase() === 'ascendant') || items[0] || null;
  const mcItem = items.find((item) => String(item?.label || '').toLowerCase() === 'midheaven') || null;
  const remaining = items.filter((item) => item !== ascItem && item !== mcItem);
  const orderedItems = [ascItem, mcItem, ...remaining].filter(Boolean);

  return (
    <div className={`${panelCls} flex min-h-[21rem] flex-col md:min-h-[26rem] lg:min-h-[29rem]`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400" style={monoStyle}>
            Dignity Summary
          </div>
          <h3 className="mt-1 font-semibold text-sm">Almuten</h3>
        </div>
        {sect ? (
          <div className="rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
            {sect} sect
          </div>
        ) : null}
      </div>
      <div
        aria-label={`Calculation method: ${methodLabel}`}
        className="mt-2 text-[10px] text-zinc-500"
        style={serifStyle}
      >
        {methodLabel}
      </div>
      {calculationNote ? (
        <div
          role="note"
          className="mt-1 text-[10px] text-zinc-500"
          style={serifStyle}
        >
          {calculationNote}
        </div>
      ) : null}

      <div className="mt-3 astro-scroll-shell min-h-0 flex-1">
        <div className="astro-scroll">
          {!orderedItems.length ? (
            <div className="text-sm text-zinc-500">No almuten data available.</div>
          ) : (
            <div className="divide-y divide-zinc-100">
              {orderedItems.map((item, index) => {
                const leaderDetails = getLeaderDetails(item);
                const primaryBreakdown = leaderDetails.length === 1
                  ? formatBreakdownChips(leaderDetails[0]?.breakdown)
                  : [];
                const isPrimary = index === 0;
                return (
                  <div key={item?.key || item?.label || index} className={`${index === 0 ? 'pt-0' : 'pt-3'} pb-3 last:pb-0`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400" style={monoStyle}>
                          <span>Almuten of </span>
                          <span>{formatPointLabel(item?.label)}</span>
                        </div>
                        <div className={`mt-1 leading-tight text-zinc-900 ${isPrimary ? 'text-[1.05rem]' : 'text-[15px]'}`} style={serifStyle}>
                          {formatLeaderLabel(leaderDetails)}
                        </div>
                        <div className="mt-1 text-[11px] text-zinc-500">
                          {formatZodiacPosition(item?.sign, item?.degree_in_sign)}
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className={`${isPrimary ? 'text-[1.35rem]' : 'text-[1.05rem]'} leading-none text-zinc-900`} style={serifStyle}>
                          {Number(item?.leader_score || 0)}
                        </div>
                        <div className="mt-1 text-[8px] font-semibold uppercase tracking-[0.16em] text-zinc-400" style={monoStyle}>
                          points
                        </div>
                      </div>
                    </div>
                    {primaryBreakdown.length ? (
                      <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-[10px] text-zinc-500" style={monoStyle}>
                        {primaryBreakdown.map((chip) => (
                          <span key={chip}>{chip}</span>
                        ))}
                      </div>
                    ) : null}
                    {leaderDetails.length > 1 ? (
                      <div className="mt-2 space-y-1.5">
                        {leaderDetails.map((detail) => {
                          const breakdown = formatBreakdownChips(detail.breakdown);
                          return (
                            <div
                              key={detail.planet}
                              aria-label={`${detail.planet} dignity breakdown`}
                              className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[10px] text-zinc-500"
                              style={monoStyle}
                            >
                              <span className="font-semibold text-zinc-600">{detail.planet}</span>
                              {breakdown.length ? breakdown.map((chip) => (
                                <span key={chip}>{chip}</span>
                              )) : (
                                <span>No scored dignity</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
