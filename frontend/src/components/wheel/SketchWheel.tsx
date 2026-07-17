import React from 'react';

export type PlanetInput = {
  id: string;
  glyph: string;
  lon: number;
  retro?: boolean;
  house?: number;
  label?: string;
};

export type Aspect = {
  a: string;
  b: string;
  type: 'conj' | 'opp' | 'trine' | 'square' | 'sextile';
  orb: number;
  maxOrb: number;
  label?: string;
  phase?: string;
  symbol?: string;
  orbText?: string;
};

export type WheelProps = {
  asc: number;
  midheaven?: number;
  cusps?: number[];
  planets: PlanetInput[];
  aspects?: Aspect[];
  size?: number;
  showAspects?: boolean;
};

const SIGN_GLYPHS = ['♈︎','♉︎','♊︎','♋︎','♌︎','♍︎','♎︎','♏︎','♐︎','♑︎','♒︎','♓︎'];
const SIGN_ABBRS = ['Ari','Tau','Gem','Can','Leo','Vir','Lib','Sco','Sag','Cap','Aqu','Pis'];
const ROMANS = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII'];
const ASPECT_SYMBOL: Record<Aspect['type'], string> = {
  conj: '☌',
  opp: '☍',
  trine: '△',
  square: '□',
  sextile: '⚹',
};
const MIN_SEP_DEG = 8;
const ZODIAC_FONT_FAMILY = '"Noto Sans Symbols 2","Segoe UI Symbol","Apple Symbols",serif';

function normalizeDegrees(value: number): number {
  return ((value % 360) + 360) % 360;
}

function separatedAngles(planets: Array<{ id: string; lon: number }>): Map<string, number> {
  if (!planets.length) return new Map();
  const arranged = planets
    .map((planet) => ({ ...planet, disp: normalizeDegrees(planet.lon) }))
    .sort((left, right) => left.disp - right.disp);

  for (let pass = 0; pass < 6; pass += 1) {
    for (let index = 0; index < arranged.length; index += 1) {
      const prevIndex = (index - 1 + arranged.length) % arranged.length;
      const gap = (arranged[index].disp - arranged[prevIndex].disp + 360) % 360;
      if (gap < MIN_SEP_DEG) {
        const push = (MIN_SEP_DEG - gap) / 2;
        arranged[index].disp = (arranged[index].disp + push) % 360;
        arranged[prevIndex].disp = (arranged[prevIndex].disp - push + 360) % 360;
      }
    }
  }

  return new Map(arranged.map((planet) => [planet.id, planet.disp]));
}

function aspectStroke(type: Aspect['type']): string {
  if (type === 'conj') return '#0f766e';
  if (type === 'opp') return '#dc2626';
  if (type === 'square') return '#c2410c';
  if (type === 'trine') return '#16a34a';
  return '#4f46e5';
}

function aspectPhaseMode(phase?: string): 'applying' | 'separating' | 'neutral' {
  const normalized = String(phase || '').trim().toLowerCase();
  if (normalized === 'applying') return 'applying';
  if (normalized === 'separating') return 'separating';
  return 'neutral';
}

function aspectKey(aspect: Aspect): string {
  const ids = [aspect.a, aspect.b].sort();
  return `${ids[0]}|${ids[1]}|${aspect.type}`;
}

function formatDegreeLabel(lon: number, withSign = false): string {
  const normalized = normalizeDegrees(lon);
  const signIndex = Math.floor(normalized / 30);
  const within = normalized - signIndex * 30;
  const degrees = Math.floor(within);
  const minutes = Math.round((within - degrees) * 60);
  const label = `${degrees}°${String(minutes).padStart(2, '0')}'`;
  return withSign ? `${label} ${SIGN_ABBRS[signIndex]}` : label;
}

function formatAspectPhase(phase?: string): string {
  const normalized = String(phase || '').trim().toLowerCase();
  if (normalized === 'applying') return 'app';
  if (normalized === 'separating') return 'sep';
  return '';
}

const SketchWheel: React.FC<WheelProps> = ({
  asc,
  midheaven,
  cusps,
  planets,
  aspects = [],
  size,
  showAspects = false,
}) => {
  const wrapRef = React.useRef<HTMLDivElement>(null);
  const [box, setBox] = React.useState<number>(size ?? 620);
  React.useEffect(() => {
    if (size || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect?.width;
      if (width) setBox(Math.max(320, Math.min(980, width)));
    });
    if (wrapRef.current) observer.observe(wrapRef.current);
    return () => observer.disconnect();
  }, [size]);

  const resolvedSize = size ?? box;
  const center = resolvedSize / 2;
  const rOuter = resolvedSize * 0.472;
  const rSigns = resolvedSize * 0.406;
  const rHouses = resolvedSize * 0.35;
  const rPlanets = resolvedSize * 0.284;
  const rAspects = resolvedSize * 0.29;
  const [hoverId, setHoverId] = React.useState<string | null>(null);
  const [pinId, setPinId] = React.useState<string | null>(null);
  const activeId = pinId ?? hoverId;

  const toRadians = React.useCallback((degrees: number) => (degrees * Math.PI) / 180, []);
  const theta = React.useCallback((lon: number) => toRadians((-(lon - asc) + 180)), [asc, toRadians]);
  const pointAt = React.useCallback((radius: number, angle: number): [number, number] => ([
    center + radius * Math.cos(angle),
    center + radius * Math.sin(angle),
  ]), [center]);

  const resolvedCusps = React.useMemo(() => {
    if (Array.isArray(cusps) && cusps.length === 12) return cusps.map((cusp) => normalizeDegrees(Number(cusp) || 0));
    return Array.from({ length: 12 }, (_, index) => normalizeDegrees(asc + index * 30));
  }, [asc, cusps]);

  const ascLongitude = normalizeDegrees(asc);
  const midheavenLongitude = normalizeDegrees(
    Number.isFinite(Number(midheaven)) ? Number(midheaven) : resolvedCusps[9] ?? asc + 90,
  );
  const angleMap = React.useMemo(
    () => separatedAngles(planets.map((planet) => ({ id: planet.id, lon: planet.lon }))),
    [planets],
  );
  const planetLookup = React.useMemo(
    () => new Map(planets.map((planet) => [planet.id, planet])),
    [planets],
  );
  const validAspects = React.useMemo(
    () => aspects.filter((aspect) => planetLookup.has(aspect.a) && planetLookup.has(aspect.b)),
    [aspects, planetLookup],
  );
  const aspectIndex = React.useMemo(() => {
    const map = new Map<string, Aspect[]>();
    validAspects.forEach((aspect) => {
      map.set(aspect.a, [...(map.get(aspect.a) || []), aspect]);
      map.set(aspect.b, [...(map.get(aspect.b) || []), aspect]);
    });
    return map;
  }, [validAspects]);
  const activeAspects = React.useMemo(() => (
    activeId ? (aspectIndex.get(activeId) || []) : []
  ), [activeId, aspectIndex]);
  const highlightedAspectKeys = React.useMemo(
    () => new Set(activeAspects.map((aspect) => aspectKey(aspect))),
    [activeAspects],
  );

  const planetLabelRadius = React.useCallback((planetId: string) => {
    const current = angleMap.get(planetId);
    if (current == null) return rPlanets + 16;
    const crowded = planets.some((planet) => {
      if (planet.id === planetId) return false;
      const other = angleMap.get(planet.id);
      if (other == null) return false;
      const delta = Math.abs((((other - current + 540) % 360) - 180));
      return delta < 8;
    });
    return crowded ? rPlanets + 26 : rPlanets + 16;
  }, [angleMap, planets, rPlanets]);

  const tooltipRows = React.useMemo(() => {
    if (!activeId) return [];
    return activeAspects
      .slice()
      .sort((left, right) => left.orb - right.orb)
      .slice(0, 5)
      .map((aspect) => {
        const partnerId = aspect.a === activeId ? aspect.b : aspect.a;
        const partner = planetLookup.get(partnerId);
        const phase = formatAspectPhase(aspect.phase);
        const orbText = aspect.orbText || `${Math.abs(aspect.orb).toFixed(1)}°`;
        const symbol = aspect.symbol || ASPECT_SYMBOL[aspect.type];
        return `${symbol} ${partner?.label || partnerId} · ${orbText}${phase ? ` · ${phase}` : ''}`;
      });
  }, [activeAspects, activeId, planetLookup]);

  return (
    <div ref={wrapRef} className="h-full w-full">
      <svg
        viewBox={`0 0 ${resolvedSize} ${resolvedSize}`}
        className="h-full w-full select-none"
        onMouseLeave={() => setHoverId(null)}
      >
        <g>
          <circle cx={center} cy={center} r={rOuter + 6} fill="#ffffff" />
          <circle cx={center} cy={center} r={rOuter} fill="#ffffff" stroke="#e5e7eb" strokeWidth={1.6} />
          <circle cx={center} cy={center} r={rHouses} fill="#fafafa" stroke="#e5e7eb" strokeWidth={1.1} />
          <circle cx={center} cy={center} r={rHouses * 0.56} fill="#ffffff" stroke="#eceef1" strokeWidth={0.9} />

          {Array.from({ length: 72 }, (_, index) => index * 5).map((degrees) => {
            const angle = theta(degrees);
            const [x1, y1] = pointAt(rOuter, angle);
            const length = degrees % 30 === 0 ? 15 : degrees % 10 === 0 ? 10 : 5;
            const [x2, y2] = pointAt(rOuter - length, angle);
            return (
              <line
                key={`tick-${degrees}`}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="#b8bec7"
                strokeWidth={degrees % 30 === 0 ? 1.1 : 0.65}
              />
            );
          })}

          {Array.from({ length: 12 }, (_, index) => {
            const angle = theta(index * 30);
            const [x1, y1] = pointAt(rOuter, angle);
            const [x2, y2] = pointAt(rHouses, angle);
            return (
              <line
                key={`sign-divider-${index}`}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="#d6dbe2"
                strokeWidth={0.9}
              />
            );
          })}

          {resolvedCusps.map((cusp, index) => {
            const angle = theta(cusp);
            const [x1, y1] = pointAt(rHouses, angle);
            const [x2, y2] = pointAt(rHouses * 0.56, angle);
            return (
              <line
                key={`house-divider-${index}`}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="#e6e9ee"
                strokeWidth={0.8}
              />
            );
          })}

          {SIGN_GLYPHS.map((glyph, index) => {
            const angle = theta(index * 30 + 15);
            const [x, y] = pointAt(rSigns, angle);
            return (
              <text
                key={`sign-${glyph}`}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={17}
                fill="#4b5563"
                fontFamily={ZODIAC_FONT_FAMILY}
              >
                {glyph}
              </text>
            );
          })}

          {ROMANS.map((label, index) => {
            const angle = theta(resolvedCusps[index] + 15);
            const [x, y] = pointAt(rHouses * 0.81, angle);
            return (
              <text
                key={`house-label-${label}`}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={10.5}
                fill="#9aa3af"
              >
                {label}
              </text>
            );
          })}

          {[
            { lon: ascLongitude, label: 'ASC', active: true, dashed: false },
            { lon: midheavenLongitude, label: 'MC', active: true, dashed: false },
            { lon: normalizeDegrees(ascLongitude + 180), label: 'DSC', active: false, dashed: true },
            { lon: normalizeDegrees(midheavenLongitude + 180), label: 'IC', active: false, dashed: true },
          ].map((angle) => {
            const thetaValue = theta(angle.lon);
            const [x1, y1] = pointAt(rOuter + 5, thetaValue);
            const [x2, y2] = pointAt(rOuter - 18, thetaValue);
            const [labelX, labelY] = pointAt(rOuter + 18, thetaValue);
            const xDelta = labelX - center;
            const textAnchor =
              Math.abs(xDelta) < 8
                ? 'middle'
                : xDelta > 0
                  ? 'start'
                  : 'end';
            return (
              <g key={`angle-${angle.label}`}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={angle.active ? '#111827' : '#9ca3af'}
                  strokeWidth={angle.active ? 1.55 : 0.9}
                  strokeDasharray={angle.dashed ? '3 3' : undefined}
                />
                <text
                  x={labelX}
                  y={labelY}
                  textAnchor={textAnchor}
                  dominantBaseline="middle"
                  fontSize={8.5}
                  fill={angle.active ? '#111827' : '#9ca3af'}
                  letterSpacing="0.18em"
                >
                  {angle.label}
                </text>
              </g>
            );
          })}

          {showAspects && activeId && validAspects.map((aspect, index) => {
            const left = planetLookup.get(aspect.a);
            const right = planetLookup.get(aspect.b);
            if (!left || !right) return null;
            const [x1, y1] = pointAt(rAspects, theta(left.lon));
            const [x2, y2] = pointAt(rAspects, theta(right.lon));
            const key = aspectKey(aspect);
            const highlighted = highlightedAspectKeys.has(key);
            if (!highlighted) return null;
            const phaseMode = aspectPhaseMode(aspect.phase);
            const controlStrength = phaseMode === 'applying' ? 0.16 : phaseMode === 'separating' ? 0.08 : 0.12;
            const controlY = center + (y1 + y2 > center * 2 ? -resolvedSize * controlStrength : resolvedSize * controlStrength);
            const controlX = center;
            const path = `M ${x1.toFixed(2)} ${y1.toFixed(2)} Q ${controlX.toFixed(2)} ${controlY.toFixed(2)} ${x2.toFixed(2)} ${y2.toFixed(2)}`;
            return (
              <path
                key={`aspect-${key}-${index}`}
                data-testid="wheel-aspect-line"
                data-phase={phaseMode}
                d={path}
                stroke={aspectStroke(aspect.type)}
                fill="none"
                strokeWidth={phaseMode === 'applying' ? 2.25 : 1.85}
                strokeOpacity={phaseMode === 'applying' ? 0.9 : phaseMode === 'separating' ? 0.72 : 0.82}
                strokeDasharray={phaseMode === 'separating' ? '5 4' : undefined}
                strokeLinecap="round"
              />
            );
          })}

          {planets.map((planet) => {
            const displayLon = angleMap.get(planet.id) ?? normalizeDegrees(planet.lon);
            const angle = theta(displayLon);
            const labelRadius = planetLabelRadius(planet.id);
            const [glyphX, glyphY] = pointAt(labelRadius, angle);
            const crowded = labelRadius > rPlanets + 18;
            const labelFontSize = crowded ? 8.8 : 10;
            const isActive = activeId === planet.id;
            const labelDirection = glyphX >= center ? 1 : -1;
            const labelX = labelDirection > 0 ? 16 : -16;
            const labelAnchor = labelDirection > 0 ? 'start' : 'end';
            return (
              <g
                key={planet.id}
                data-testid={`wheel-planet-${planet.id}`}
                data-planet-id={planet.id}
                transform={`translate(${glyphX},${glyphY})`}
                style={{ cursor: 'pointer', transition: 'transform .35s ease-out' }}
                onMouseEnter={() => setHoverId(planet.id)}
                onMouseLeave={() => setHoverId(null)}
                onClick={() => setPinId((current) => (current === planet.id ? null : planet.id))}
              >
                {isActive ? (
                  <circle cx={0} cy={0} r={13} fill="#f8fafc" stroke="#d7dde5" strokeWidth={1} />
                ) : null}
                <text x={0} y={0} textAnchor="middle" dominantBaseline="middle" fontSize={16} fill="#111827">
                  {planet.glyph}
                </text>
                {planet.retro ? (
                  <text x={9} y={-7} textAnchor="middle" dominantBaseline="middle" fontSize={7.5} fill="#b45309">
                    ℞
                  </text>
                ) : null}
                <text
                  x={labelX}
                  y={0}
                  textAnchor={labelAnchor}
                  dominantBaseline="middle"
                  fontSize={labelFontSize}
                  fill="#525866"
                >
                  {formatDegreeLabel(planet.lon)}
                  {planet.house ? ` · H${planet.house}` : ''}
                </text>
              </g>
            );
          })}

          {activeId ? (() => {
            const activePlanet = planetLookup.get(activeId);
            if (!activePlanet) return null;
            const hasAspectRows = tooltipRows.length > 0;
            const width = hasAspectRows ? 210 : 176;
            const extraRowCount = tooltipRows.length + (activeAspects.length > tooltipRows.length ? 1 : 0);
            const height = 58 + (hasAspectRows ? 18 + extraRowCount * 14 : 22);
            const tx = center - width / 2;
            const ty = center - height / 2;
            return (
              <g data-testid="wheel-tooltip" pointerEvents="none">
                <rect x={tx} y={ty} width={width} height={height} rx={12} fill="#ffffff" stroke="#e5e7eb" />
                <text x={tx + 12} y={ty + 18} fontSize={12} fill="#111827">
                  {activePlanet.label ?? activePlanet.id}
                </text>
                <text x={tx + 12} y={ty + 34} fontSize={11} fill="#4b5563">
                  {formatDegreeLabel(activePlanet.lon, true)}
                </text>
                <text x={tx + 12} y={ty + 48} fontSize={10} fill="#9ca3af">
                  {activePlanet.house ? `House ${activePlanet.house}` : ''}
                </text>
                {hasAspectRows ? (
                  <>
                    <line x1={tx + 10} y1={ty + 58} x2={tx + width - 10} y2={ty + 58} stroke="#eef2f7" strokeWidth={1} />
                    <text x={tx + 12} y={ty + 72} fontSize={10} fill="#94a3b8">
                      Aspects
                    </text>
                    {tooltipRows.map((row, index) => (
                      <text key={`${row}-${index}`} x={tx + 12} y={ty + 88 + index * 14} fontSize={10.5} fill="#475569">
                        {row}
                      </text>
                    ))}
                    {activeAspects.length > tooltipRows.length ? (
                      <text x={tx + 12} y={ty + 88 + tooltipRows.length * 14} fontSize={10} fill="#94a3b8">
                        +{activeAspects.length - tooltipRows.length} more
                      </text>
                    ) : null}
                  </>
                ) : (
                  <>
                    <line x1={tx + 10} y1={ty + 58} x2={tx + width - 10} y2={ty + 58} stroke="#eef2f7" strokeWidth={1} />
                    <text x={tx + 12} y={ty + 74} fontSize={10} fill="#94a3b8">
                      No major aspects in scope
                    </text>
                  </>
                )}
              </g>
            );
          })() : null}
        </g>
      </svg>
    </div>
  );
};

export default SketchWheel;
