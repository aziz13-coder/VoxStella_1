import React, { useEffect, useMemo, useRef, useState } from 'react';

import { AstroClockAPI } from './api.mjs';

const PlanetSymbols = {
  Sun: '\u2609',
  Moon: '\u263D',
  Mercury: '\u263F',
  Venus: '\u2640',
  Mars: '\u2642',
  Jupiter: '\u2643',
  Saturn: '\u2644',
  Uranus: '\u2645',
  Neptune: '\u2646',
  Pluto: '\u2647',
};

const CLASSICAL_PLANETS = new Set(['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']);

function buildLocalCompassData({ planets, houseCusps, includeModern = false }) {
  if (!Array.isArray(planets) || !planets.length || !Array.isArray(houseCusps) || !houseCusps.length) {
    return null;
  }
  const asc = Number(houseCusps[0]);
  if (!Number.isFinite(asc)) {
    return null;
  }
  const azimuths = planets
    .filter((planet) => planet && typeof planet === 'object' && planet.planet && planet.longitude != null)
    .filter((planet) => includeModern || CLASSICAL_PLANETS.has(planet.planet))
    .map((planet) => {
      const longitude = Number(planet.longitude);
      if (!Number.isFinite(longitude)) return null;
      return {
        planet: planet.planet,
        azimuth_deg: (longitude - asc + 90.0 + 360.0) % 360.0,
      };
    })
    .filter(Boolean);
  if (!azimuths.length) {
    return null;
  }
  return { azimuths, ascendant: asc };
}

function labelDistance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export default function CompassTile({
  includeModern = false,
  timestamp,
  mode,
  location,
  planets = [],
  houseCusps = [],
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [remoteData, setRemoteData] = useState(null);
  const requestIdRef = useRef(0);

  const localData = useMemo(
    () => buildLocalCompassData({ planets, houseCusps, includeModern }),
    [houseCusps, includeModern, planets]
  );
  const displayData = localData || remoteData;
  const hasDisplayData = Array.isArray(displayData?.azimuths) && displayData.azimuths.length > 0;

  useEffect(() => {
    if (localData) {
      setLoading(false);
      setError(null);
      return undefined;
    }
    if (!timestamp && !location && !mode) {
      return undefined;
    }
    let cancelled = false;
    const requestId = ++requestIdRef.current;

    async function fetchFallbackCompass() {
      setLoading(true);
      setError(null);
      try {
        const res = await AstroClockAPI.getCompass({ includeModern });
        if (cancelled || requestId !== requestIdRef.current) return;
        if (res?.success) {
          setRemoteData(res.data || null);
        } else {
          setError('Failed to load bearings');
        }
      } catch (e) {
        if (cancelled || requestId !== requestIdRef.current) return;
        const msg = String(e?.message || '');
        if (msg.includes('license_required') || msg.includes('license_invalid')) {
          setError('License required');
        } else {
          setError('Failed to load bearings');
        }
      } finally {
        if (!cancelled && requestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    }

    fetchFallbackCompass();
    return () => {
      cancelled = true;
    };
  }, [includeModern, localData, location, mode, timestamp]);

  const svg = useMemo(() => {
    if (!hasDisplayData) return null;

    const size = 320;
    const cx = size / 2;
    const cy = size / 2;
    const r = 126;
    const toRad = (degrees) => (Number(degrees) || 0) * Math.PI / 180;
    const pointAt = (azDeg, radius = r) => {
      const angle = toRad(90 - ((Number(azDeg) || 0) % 360));
      const x = cx + radius * Math.cos(angle);
      const y = cy - radius * Math.sin(angle);
      return [x, y];
    };

    const labelLayout = new Map();
    const ordered = [...displayData.azimuths]
      .map((entry, index) => ({ entry, index }))
      .sort((a, b) => Number(a.entry?.azimuth_deg || 0) - Number(b.entry?.azimuth_deg || 0));
    const placedLabels = [];

    for (const item of ordered) {
      let offset = 18;
      let labelPoint = pointAt(item.entry.azimuth_deg, r + offset);
      let attempts = 0;
      while (
        placedLabels.some((placed) => labelDistance(placed, { x: labelPoint[0], y: labelPoint[1] }) < 18) &&
        attempts < 4
      ) {
        offset += 10;
        labelPoint = pointAt(item.entry.azimuth_deg, r + offset);
        attempts += 1;
      }
      const nextPoint = { x: labelPoint[0], y: labelPoint[1] };
      placedLabels.push(nextPoint);
      labelLayout.set(item.index, { x: nextPoint.x, y: nextPoint.y, offset });
    }

    const rings = [r, r * 0.66, r * 0.33].map((ringRadius, index) => (
      <circle
        key={index}
        cx={cx}
        cy={cy}
        r={ringRadius}
        fill="none"
        stroke="#d4d4d8"
        strokeWidth="1"
      />
    ));

    const cardinals = [
      { t: 'N', a: 0 },
      { t: 'E', a: 90 },
      { t: 'S', a: 180 },
      { t: 'W', a: 270 },
    ].map((cardinal, index) => {
      const point = pointAt(cardinal.a, r + 18);
      return (
        <text
          key={index}
          x={point[0]}
          y={point[1]}
          fontSize="12"
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#3f3f46"
        >
          {cardinal.t}
        </text>
      );
    });

    const dots = displayData.azimuths.map((item, index) => {
      const [x, y] = pointAt(item.azimuth_deg);
      const label = labelLayout.get(index) || { x, y: y - 16, offset: 18 };
      const symbol = PlanetSymbols[item.planet] || item.planet;
      const needsGuide = label.offset > 18;
      return (
        <g key={`${item.planet}-${index}`}>
          {needsGuide ? (
            <line
              x1={x}
              y1={y}
              x2={label.x}
              y2={label.y + 4}
              stroke="#9ca3af"
              strokeWidth="1"
            />
          ) : null}
          <circle cx={x} cy={y} r={4} fill="#111827" />
          <text
            x={label.x}
            y={label.y}
            fontSize="12"
            fontWeight="500"
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#111827"
          >
            {symbol}
          </text>
        </g>
      );
    });

    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox={`0 0 ${size} ${size}`}
        className="block h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {rings}
        <circle cx={cx} cy={cy} r={3} fill="#111827" />
        {dots}
        {cardinals}
      </svg>
    );
  }, [displayData, hasDisplayData]);

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-sm">Compass Bearings</h3>
        {loading && !hasDisplayData ? (
          <span className="text-[11px] font-medium text-zinc-500">Updating...</span>
        ) : null}
      </div>
      <div className="mt-3 rounded-[20px] border border-zinc-100 bg-zinc-50/70 p-3">
        {error ? <div className="text-sm text-red-600">{error}</div> : null}
        {!error && hasDisplayData ? (
          <div className="mx-auto w-full max-w-[280px]">{svg}</div>
        ) : null}
        {!error && !hasDisplayData && loading ? (
          <div className="flex min-h-[240px] items-center justify-center text-sm text-zinc-500">
            Updating bearings...
          </div>
        ) : null}
        {!error && !hasDisplayData && !loading ? (
          <div className="flex min-h-[240px] items-center justify-center text-sm text-zinc-500">
            No bearing data available.
          </div>
        ) : null}
      </div>
    </div>
  );
}
