import React from 'react';
import { beforeAll, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import SketchWheel from '../components/wheel/SketchWheel.tsx';

beforeAll(() => {
  if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class ResizeObserver {
      observe() {}
      disconnect() {}
      unobserve() {}
    };
  }
});

describe('SketchWheel', () => {
  it('shows the hovered planet aspects inside the tooltip', () => {
    render(
      <div style={{ width: 640, height: 640 }}>
        <SketchWheel
          asc={15}
          midheaven={285}
          planets={[
            { id: 'Sun', glyph: '☉', lon: 18, house: 1, label: 'Sun' },
            { id: 'Saturn', glyph: '♄', lon: 138, house: 5, label: 'Saturn' },
            { id: 'Mars', glyph: '♂', lon: 108, house: 4, label: 'Mars' },
          ]}
          aspects={[
            {
              a: 'Sun',
              b: 'Saturn',
              type: 'trine',
              orb: 2.1,
              maxOrb: 8,
              symbol: '△',
              orbText: '2.1°',
              phase: 'applying',
            },
            {
              a: 'Sun',
              b: 'Mars',
              type: 'square',
              orb: 4.0,
              maxOrb: 8,
              symbol: '□',
              orbText: '4.0°',
              phase: 'separating',
            },
          ]}
          showAspects
        />
      </div>,
    );

    expect(screen.queryAllByTestId('wheel-aspect-line')).toHaveLength(0);

    fireEvent.mouseEnter(screen.getByTestId('wheel-planet-Sun'));

    expect(screen.getByTestId('wheel-tooltip')).toBeInTheDocument();
    const lines = screen.getAllByTestId('wheel-aspect-line');
    expect(lines).toHaveLength(2);
    expect(lines.some((line) => line.getAttribute('data-phase') === 'applying')).toBe(true);
    expect(lines.some((line) => line.getAttribute('data-phase') === 'separating')).toBe(true);
    expect(lines.find((line) => line.getAttribute('data-phase') === 'separating')?.getAttribute('stroke-dasharray')).toBe('5 4');
    expect(screen.getByText('Aspects')).toBeInTheDocument();
    expect(screen.getByText('△ Saturn · 2.1° · app')).toBeInTheDocument();
    expect(screen.getByText('□ Mars · 4.0° · sep')).toBeInTheDocument();

    fireEvent.mouseLeave(screen.getByTestId('wheel-planet-Sun'));

    expect(screen.queryAllByTestId('wheel-aspect-line')).toHaveLength(0);
  });

  it('explains when the hovered planet has no major aspects in scope', () => {
    render(
      <div style={{ width: 640, height: 640 }}>
        <SketchWheel
          asc={15}
          midheaven={285}
          planets={[
            { id: 'Sun', glyph: '☉', lon: 18, house: 1, label: 'Sun' },
            { id: 'Saturn', glyph: '♄', lon: 138, house: 5, label: 'Saturn' },
          ]}
          aspects={[]}
          showAspects
        />
      </div>,
    );

    fireEvent.mouseEnter(screen.getByTestId('wheel-planet-Sun'));

    expect(screen.getByTestId('wheel-tooltip')).toBeInTheDocument();
    expect(screen.getByText('No major aspects in scope')).toBeInTheDocument();
  });
});
