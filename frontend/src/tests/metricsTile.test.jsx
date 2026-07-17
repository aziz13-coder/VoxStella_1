import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import MetricsTile from '../features/astroclock/MetricsTile.jsx';

describe('MetricsTile', () => {
  it('renders stacked balance bars and signed affliction rows', () => {
    render(
      <MetricsTile
        specialDegrees={['27 Aries']}
        metrics={{
          element_balance: { Fire: 45, Earth: 18, Air: 18, Water: 19 },
          modality_balance: { Cardinal: 55, Fixed: 27, Mutable: 18 },
          angle_aspects: [
            { afflicting: true, severity: 'severe', planet: 'Mars', aspect: 'Square', angle: 'ASC', orb: 4.37 },
            { afflicting: true, severity: 'severe', planet: 'Mars', aspect: 'Square', angle: 'DSC', orb: 4.37 },
            { afflicting: true, severity: 'moderate', planet: 'Jupiter', aspect: 'Opposition', angle: 'ASC', orb: 5.2 },
          ],
          planetary_aspects: [
            { afflicting: true, severity: 'severe', planet1: 'Moon', aspect: 'Square', planet2: 'North Node', orb: 0.89 },
            { afflicting: true, severity: 'moderate', planet1: 'Mercury', aspect: 'Conjunction', planet2: 'Mars', orb: 0.68 },
          ],
        }}
      />,
    );

    expect(screen.getByText('Fire 45')).toBeInTheDocument();
    expect(screen.getByText(/Fire-heavy\./)).toBeInTheDocument();
    expect(screen.getByText('Cardinal 55')).toBeInTheDocument();
    expect(screen.getByText(/Cardinal-led\./)).toBeInTheDocument();
    expect(screen.getByText('3 active - Mars and Jupiter pressure the angles.')).toBeInTheDocument();
    expect(screen.getAllByText('-4.37°')).toHaveLength(2);
    expect(screen.getByText('Mars Square ASC')).toBeInTheDocument();
    expect(screen.getByText('Moon Square North Node')).toBeInTheDocument();
  });
});
