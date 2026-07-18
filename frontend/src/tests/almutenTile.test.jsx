import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';

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
    expect(screen.getByLabelText('Calculation method: Lilly · sect ruler')).toBeInTheDocument();
  });

  it('rounds degree minutes and carries across the next sign', () => {
    render(
      <AlmutenTile
        almutens={{
          sect: 'Day',
          items: [
            {
              key: 'asc',
              label: 'Ascendant',
              sign: 'Pisces',
              degree_in_sign: 29.999,
              leader: 'Jupiter',
              leader_score: 5,
              leader_breakdown: { domicile: 5 },
            },
            {
              key: 'mc',
              label: 'Midheaven',
              sign: 'Cancer',
              degree_in_sign: 5.999,
              leader: 'Moon',
              leader_score: 5,
              leader_breakdown: { domicile: 5 },
            },
          ],
        }}
      />
    );

    expect(screen.getByText("Aries 0°00'")).toBeInTheDocument();
    expect(screen.getByText("Cancer 6°00'")).toBeInTheDocument();
  });

  it('shows the backend method label and each tied leader own dignity breakdown', () => {
    render(
      <AlmutenTile
        almutens={{
          sect: 'Day',
          method: {
            id: 'lilly_sect',
            label: 'Lilly · sect ruler',
            terms: 'Egyptian',
            faces: 'Chaldean',
          },
          items: [
            {
              key: 'asc',
              label: 'Ascendant',
              sign: 'Aries',
              degree_in_sign: 12.25,
              leader: 'Sun',
              leaders: ['Sun', 'Mars'],
              leader_score: 4,
              leader_breakdown: { exaltation: 4 },
              leader_details: [
                {
                  planet: 'Sun',
                  score: 4,
                  dignities: ['exaltation'],
                  breakdown: { exaltation: 4 },
                },
                {
                  planet: 'Mars',
                  score: 4,
                  dignities: ['triplicity', 'face'],
                  breakdown: { triplicity: 3, face: 1 },
                },
              ],
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Sun / Mars')).toBeInTheDocument();
    expect(screen.getByLabelText('Calculation method: Lilly · sect ruler')).toBeInTheDocument();

    const sunBreakdown = screen.getByLabelText('Sun dignity breakdown');
    expect(within(sunBreakdown).getByText('Exaltation +4')).toBeInTheDocument();
    expect(within(sunBreakdown).queryByText('Triplicity +3')).not.toBeInTheDocument();

    const marsBreakdown = screen.getByLabelText('Mars dignity breakdown');
    expect(within(marsBreakdown).getByText('Triplicity +3')).toBeInTheDocument();
    expect(within(marsBreakdown).getByText('Face +1')).toBeInTheDocument();
    expect(within(marsBreakdown).queryByText('Exaltation +4')).not.toBeInTheDocument();
  });

  it('recovers tied dignity details from legacy candidate rows', () => {
    render(
      <AlmutenTile
        almutens={{
          items: [
            {
              key: 'asc',
              label: 'Ascendant',
              sign: 'Libra',
              degree_in_sign: 5,
              leader: 'Saturn',
              leaders: ['Saturn', 'Venus'],
              leader_score: 4,
              leader_breakdown: { exaltation: 4 },
              candidates: [
                { planet: 'Saturn', score: 4, breakdown: { exaltation: 4 } },
                { planet: 'Venus', score: 4, breakdown: { triplicity: 3, face: 1 } },
              ],
            },
          ],
        }}
      />
    );

    const saturnBreakdown = screen.getByLabelText('Saturn dignity breakdown');
    expect(within(saturnBreakdown).getByText('Exaltation +4')).toBeInTheDocument();

    const venusBreakdown = screen.getByLabelText('Venus dignity breakdown');
    expect(within(venusBreakdown).getByText('Triplicity +3')).toBeInTheDocument();
    expect(within(venusBreakdown).getByText('Face +1')).toBeInTheDocument();
  });

  it('makes a withheld triplicity score visible when sect is unavailable', () => {
    render(
      <AlmutenTile
        almutens={{
          calculation_status: 'partial',
          withheld_dignities: ['triplicity'],
          items: [],
        }}
      />
    );

    expect(screen.getByRole('note')).toHaveTextContent('Sect unavailable · triplicity not scored');
  });
});
