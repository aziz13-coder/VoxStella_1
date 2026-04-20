import React from "react";

export type PlanetInput = {
  id: string;       // e.g., "Sun"
  glyph: string;    // ☉ ☽ ☿ ♀ ♂ ♃ ♄ etc.
  lon: number;      // 0..360
  retro?: boolean;
  house?: number;   // 1..12
  label?: string;   // optional
};

export type Aspect = {
  a: string;  // planet id
  b: string;  // planet id
  type: "conj"|"opp"|"trine"|"square"|"sextile";
  orb: number;
  maxOrb: number;
};

export type WheelProps = {
  asc: number;              // Asc longitude 0..360
  cusps?: number[];         // 12 longs; if missing, equal houses from asc
  planets: PlanetInput[];
  aspects?: Aspect[];       // optional precomputed
  size?: number;            // px; if omitted, auto-fit parent width
  showAspects?: boolean;    // default false
};

const SIGNS = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"];
const SIGN_ABBRS = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"];

// Minimum visual separation between adjacent planet display angles
const MIN_SEP_DEG = 8;

function separatedAngles(planets: { id: string; lon: number }[]): Map<string, number> {
  if (!planets || planets.length === 0) return new Map();
  const arr = planets
    .map((p) => ({ ...p, disp: ((p.lon % 360) + 360) % 360 }))
    .sort((a, b) => a.disp - b.disp);

  // Iterative repulsion around the circle
  for (let pass = 0; pass < 6; pass++) {
    for (let i = 0; i < arr.length; i++) {
      const prev = (i - 1 + arr.length) % arr.length;
      const gap = (arr[i].disp - arr[prev].disp + 360) % 360;
      if (gap < MIN_SEP_DEG) {
        const push = (MIN_SEP_DEG - gap) / 2;
        arr[i].disp = (arr[i].disp + push) % 360;
        arr[prev].disp = (arr[prev].disp - push + 360) % 360;
      }
    }
  }

  const out = new Map<string, number>();
  arr.forEach((p) => out.set(p.id, p.disp));
  return out;
}
const ROMANS = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"];

const SketchWheel: React.FC<WheelProps> = ({
  asc,
  cusps,
  planets,
  aspects = [],
  size,
  showAspects = false,
}) => {
  // auto-size to parent if no explicit size
  const wrapRef = React.useRef<HTMLDivElement>(null);
  const [box, setBox] = React.useState<number>(size ?? 600);
  React.useEffect(() => {
    if (size) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width;
      setBox(Math.max(280, Math.min(900, w)));
    });
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [size]);

  const SZ = size ?? box;
  const C = SZ / 2;
  const rOuter   = SZ * 0.46;
  const rSigns   = SZ * 0.40;
  const rHouses  = SZ * 0.34;
  const rPlanets = SZ * 0.28;
  const rAspects = SZ * 0.30;

  // Lens (hover zoom) state
  const uid = React.useId();
  const [mouse, setMouse] = React.useState<{ x: number; y: number; inside: boolean }>({ x: C, y: C, inside: false });
  const lensR = Math.max(60, SZ * 0.09);
  const lensScale = 1.8;
  const clipId = `lensClip-${uid}`;
  const sceneId = `wheelScene-${uid}`;
  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    setMouse({ x: e.clientX - rect.left, y: e.clientY - rect.top, inside: true });
  };

  // helpers
  const toRad = (d: number) => (d * Math.PI) / 180;
  // View angle with ASC at 9 o'clock, CCW zodiac
  const theta = (lon: number) => toRad((-(lon - asc) + 180));
  const pt = (r: number, ang: number): [number, number] => [C + r * Math.cos(ang), C + r * Math.sin(ang)];

  // house cusps: equal houses if not provided
  const H: number[] = (cusps && cusps.length === 12)
    ? cusps
    : Array.from({ length: 12 }, (_, i) => (asc + i * 30) % 360);

  const [hoverId, setHoverId] = React.useState<string | null>(null);
  const [pinId, setPinId] = React.useState<string | null>(null);
  const activeId = pinId ?? hoverId;

  const degLabel = (lon: number, withSign = false) => {
    const L = ((lon % 360) + 360) % 360;
    const s = Math.floor(L / 30);
    const within = L - s * 30;
    const d = Math.floor(within);
    const m = Math.round((within - d) * 60);
    return withSign
      ? `${d}°${String(m).padStart(2, "0")}' ${SIGN_ABBRS[s]}`
      : `${d}°${String(m).padStart(2, "0")}'`;
  };

  const planetById = (id: string) => planets.find(p => p.id === id);

  const aspectStroke = (t: Aspect["type"]) =>
    t === "conj" ? "#0ea5e9"
      : t === "opp" ? "#ef4444"
      : t === "square" ? "#f59e0b"
      : t === "trine" ? "#22c55e"
      : "#8b5cf6"; // sextile

  return (
    <div ref={wrapRef} className="w-full h-full">
      <svg viewBox={`0 0 ${SZ} ${SZ}`} className="w-full h-full select-none" onMouseMove={onMove} onMouseLeave={() => setMouse((m) => ({ ...m, inside: false }))}>
        <style>{`.lens-fade{transition:opacity .15s ease-out}`}</style>
        <g id={sceneId}>
        {/* rings */}
        <circle cx={C} cy={C} r={rOuter+8} fill="#fff" />
        <circle cx={C} cy={C} r={rOuter} fill="#fff" stroke="#e5e7eb" strokeWidth={2}/>
        <circle cx={C} cy={C} r={rHouses} fill="#fafafa" stroke="#e5e7eb" strokeWidth={1.5}/>
        <circle cx={C} cy={C} r={rHouses*0.55} fill="#ffffff" stroke="#e5e7eb" strokeWidth={1.25}/>

        {/* ticks every 5° */}
        {Array.from({length:72},(_,i)=>i*5).map(d=>{
          const a = theta(d);
          const [x1,y1] = pt(rOuter,a);
          const len = d%30===0 ? 16 : d%10===0 ? 12 : 6;
          const [x2,y2] = pt(rOuter-len,a);
          return <line key={`t${d}`} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke="#a1a1aa" strokeWidth={d%30===0?1.25:0.75}/>;
        })}

        {/* sign separators */}
        {Array.from({length:12}).map((_,i)=>{
          const a = theta(i*30);
          const [x1,y1] = pt(rOuter,a);
          const [x2,y2] = pt(rHouses,a);
          return <line key={`s${i}`} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke="#d4d4d8" strokeWidth={1}/>;
        })}

        {/* house lines */}
        {H.map((h,i)=>{
          const a = theta(h);
          const [x1,y1] = pt(rHouses,a);
          const [x2,y2] = pt(rHouses*0.55,a);
          return <line key={`h${i}`} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke="#e4e4e7" strokeWidth={1}/>;
        })}

        {/* sign glyphs */}
        {SIGNS.map((g,i)=>{
          const a = theta(i*30 + 15);
          const [x,y] = pt(rSigns,a);
          return <text key={`g${i}`} x={x} y={y} textAnchor="middle"
            dominantBaseline="middle" fontSize={18} fill="#d1d5db">{g}</text>;
        })}

        {/* house numerals */}
        {ROMANS.map((r,i)=>{
          const a = theta(H[i] + 15);
          const [x,y] = pt(rHouses*0.80,a);
          return <text key={`r${i}`} x={x} y={y} textAnchor="middle"
            dominantBaseline="middle" fontSize={12} fill="#a1a1aa">{r}</text>;
        })}

        {/* Angles: ASC, MC, DSC, IC — from cusps when provided */}
        {(() => {
          const ascLon = (H && H.length === 12 ? H[0] : asc);
          const mcLon  = (H && H.length === 12 ? H[9] : (asc + 90) % 360);
          const dscLon = (H && H.length === 12 ? H[6] : (asc + 180) % 360);
          const icLon  = (H && H.length === 12 ? H[3] : (asc + 270) % 360);

          const drawAngle = (lon: number, label: string) => {
            const a = theta(lon);
            const [x1, y1] = pt(rOuter + 6, a);
            const [x2, y2] = pt(rOuter - 18, a);
            return (
              <g key={label}>
                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#18181b" strokeWidth={2}/>
                <text x={x1} y={y1} textAnchor="middle" dominantBaseline="middle" fontSize={10} fill="#18181b">{label}</text>
              </g>
            );
          };

          return (
            <>
              {drawAngle(ascLon, 'ASC')}
              {drawAngle(mcLon, 'MC')}
              {drawAngle(dscLon, 'DSC')}
              {drawAngle(icLon, 'IC')}
            </>
          );
        })()}

        {/* aspect lines (optional) */}
        {showAspects && aspects.filter(a => a.orb <= a.maxOrb).map((a,i)=>{
          const A = planetById(a.a); const B = planetById(a.b);
          if (!A || !B) return null;
          const [x1,y1] = pt(rAspects, theta(A.lon));
          const [x2,y2] = pt(rAspects, theta(B.lon));
          return <line key={`asp${i}`} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={aspectStroke(a.type)} strokeWidth={1.5} strokeOpacity={0.8}/>;
        })}

        {/* planets: glyph + horizontal degree label */}
        {(() => {
          // Collision-avoiding display angles map
          const angleMap = React.useMemo(() => separatedAngles(planets), [planets]);
          const labelRadius = (p: PlanetInput) => {
            const me = angleMap.get(p.id)!;
            const crowded = planets.some((q) => {
              if (q.id === p.id) return false;
              const d = Math.abs((((angleMap.get(q.id)! - me + 540) % 360) - 180));
              return d < 8; // secondary threshold
            });
            return crowded ? rPlanets + 26 : rPlanets + 16;
          };

          // Small wrapper for smooth transform animation (CSS transition)
          const PlanetGroup: React.FC<{ x: number; y: number; children: React.ReactNode }> = ({ x, y, children }) => (
            <g transform={`translate(${x},${y})`} style={{ transition: "transform .35s ease-out" }}>{children}</g>
          );

          return planets.map((p) => {
            const dispLon = angleMap.get(p.id)!;
            const a = theta(dispLon);
            const R = labelRadius(p);
            const [gx, gy] = pt(R, a);
            // Always render the degree/house label to the right of the glyph
            const glyphAnchor: "middle" = "middle";
            const labelAnchor: "start" = "start";
            const degX = 16; // fixed to the right side of the glyph
            const me = angleMap.get(p.id)!;
            const crowded = planets.some((q) => {
              if (q.id === p.id) return false;
              const d = Math.abs((((angleMap.get(q.id)! - me + 540) % 360) - 180));
              return d < 8;
            });
            const labelFont = crowded ? 10 : 11;
            const active = activeId === p.id;
            return (
              <PlanetGroup key={p.id} x={gx} y={gy}>
                <g
                  onMouseEnter={() => setHoverId(p.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onClick={() => setPinId((v) => (v === p.id ? null : p.id))}
                  style={{ cursor: "pointer" }}
                >
                  {/* removed large hover halo to keep only the glass lens */}
                  <text x={0} y={0} textAnchor={glyphAnchor} dominantBaseline="middle" fontSize={16} fill="#111827">
                    {p.glyph}
                    {p.retro ? " ℞" : ""}
                  </text>
                  <text x={degX} y={0} textAnchor={labelAnchor} dominantBaseline="middle" fontSize={labelFont} fill="#52525b">
                    {degLabel(p.lon, false)}
                    {p.house ? ` — H${p.house}` : ""}
                  </text>
                </g>
              </PlanetGroup>
            );
          });
        })()}

        {/* tooltip */}
        {activeId && (() => {
          const p = planetById(activeId);
          if (!p) return null;
          const a = theta(p.lon);
          const [x, y] = pt(rPlanets + 46, a);
          const w = 120, h = 54;
          const tx = Math.min(Math.max(x - w/2, 8), SZ - w - 8);
          const ty = Math.min(Math.max(y - h/2, 8), SZ - h - 8);
          return (
            <g>
              <rect x={tx} y={ty} width={w} height={h} rx={8} fill="#ffffff" stroke="#e5e7eb"/>
              <text x={tx+10} y={ty+18} fontSize={12} fill="#111827">{p.label ?? p.id}</text>
              <text x={tx+10} y={ty+34} fontSize={11} fill="#52525b">{degLabel(p.lon, true)}</text>
              <text x={tx+10} y={ty+48} fontSize={10} fill="#9ca3af">{p.house ? `House ${p.house}` : ""}</text>
            </g>
          );
        })()}
        </g>

        {/* Lens (hover zoom) */}
        {mouse.inside && (
          <g className="lens-fade" opacity={mouse.inside ? 1 : 0}>
            <defs>
              <clipPath id={clipId}>
                <circle cx={mouse.x} cy={mouse.y} r={lensR} />
              </clipPath>
              <filter id={`lensShadow-${uid}`} x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000" floodOpacity="0.12" />
              </filter>
            </defs>

            {/* Magnified content, clipped to a circle that follows the cursor */}
            <g clipPath={`url(#${clipId})`} pointerEvents="none">
              <use href={`#${sceneId}`}
                   transform={`translate(${(1 - lensScale) * mouse.x} ${(1 - lensScale) * mouse.y}) scale(${lensScale})`} />
              {/* faint frosted tint to feel like glass */}
              <circle cx={mouse.x} cy={mouse.y} r={lensR} fill="#ffffff" opacity="0.15" />
            </g>

            {/* lens outline */}
            <circle cx={mouse.x} cy={mouse.y} r={lensR} fill="none" stroke="#cbd5e1" strokeWidth={2}
                    filter={`url(#lensShadow-${uid})`} />
          </g>
        )}
      </svg>
    </div>
  );
};

export default SketchWheel;
