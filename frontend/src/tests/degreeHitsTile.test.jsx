import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import DegreeHitsTile from '../features/astroclock/DegreeHitsTile.jsx';


describe('DegreeHitsTile', () => {
  it('documents accepted degree formats and applies comma-separated tokens', () => {
    const onApplyDegrees = vi.fn();

    render(
      <DegreeHitsTile
        metrics={{ degree_hits: { items: [] } }}
        specialDegrees={[]}
        onApplyDegrees={onApplyDegrees}
        onClearDegrees={() => {}}
      />
    );

    expect(screen.getByPlaceholderText('e.g., 25 59 Leo, Leo 21 15')).toBeTruthy();
    expect(screen.getByText('Accepts sign-first or sign-last degrees, with optional minutes.')).toBeTruthy();

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: '25 59 Leo, Leo 21 15' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(onApplyDegrees).toHaveBeenCalledWith(['25 59 Leo', 'Leo 21 15']);
  });
});
