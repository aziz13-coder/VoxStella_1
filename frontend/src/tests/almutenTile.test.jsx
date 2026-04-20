import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import AlmutenTile from '../features/astroclock/AlmutenTile.jsx';

describe('AlmutenTile', () => {
  it('uses compact angle labels for Ascendant and Midheaven entries', () => {
    render(
      <AlmutenTile
        almutens={{
          sect: 'Night',
          items: [
            {
              key: 'asc',
              label: 'Ascendant',
              sign: 'Capricorn',
              degree_in_sign: 18.02,
              leader: 'Saturn',
              leader_score: 5,
              leader_breakdown: { domicile: 5 },
            },
            {
              key: 'mc',
              label: 'Midheaven',
              sign: 'Gemini',
              degree_in_sign: 4.5,
              leader: 'Mars',
              leader_score: 8,
              leader_breakdown: { term: 2, face: 1 },
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Asc')).toBeInTheDocument();
    expect(screen.getByText('Mid')).toBeInTheDocument();
    expect(screen.queryByText('Ascendant')).not.toBeInTheDocument();
    expect(screen.queryByText('Midheaven')).not.toBeInTheDocument();
  });
});
