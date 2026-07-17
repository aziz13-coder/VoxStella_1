import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DegreeHitsTile from '../features/astroclock/DegreeHitsTile.jsx';

const astroClockApiMock = vi.hoisted(() => ({
  getDegreeHitPoints: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

describe('DegreeHitsTile', () => {
  beforeEach(() => {
    astroClockApiMock.getDegreeHitPoints.mockReset();
  });

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

  it('does not collapse the result area when degree hits exist', () => {
    const { container } = render(
      <DegreeHitsTile
        metrics={{
          degree_hits: {
            items: [
              {
                degree: '21 53 Libra',
                count: 1,
                stack_factor: 1,
                midpoint_active: false,
                hits: [{ type: 'part', target: 'Fortune', orb: 0.16 }],
              },
            ],
          },
        }}
        specialDegrees={['21 53 Libra']}
        onApplyDegrees={() => {}}
        onClearDegrees={() => {}}
      />
    );

    expect(screen.getByText('21 53 Libra')).toBeTruthy();
    expect(screen.getByText('Fortune')).toBeTruthy();
    expect(container.firstChild.className).not.toContain('aspect-square');
    expect(screen.getByTestId('degree-hits-results').className).toContain('min-h-');
  });

  it('opens More and renders only the top active symbolic point hits', async () => {
    const topHits = Array.from({ length: 11 }, (_, index) => ({
      key: index === 0 ? 'theft_parts_334' : `point_${index}`,
      source_row: index === 0 ? 'parts#334' : `parts#${100 + index}`,
      name: index === 0 ? 'Theft' : `Point ${index}`,
      longitude: 120 + index,
      zodiac: { formatted: `${index} Leo 00` },
      point_score: index === 0 ? 1.42 : 1 - index * 0.04,
      ui_severity: index === 0 ? 'danger' : 'supportive',
      ui_color: index === 0 ? 'red' : 'green',
      category: index === 0 ? 'danger_or_loss' : 'growth_or_support',
      hits: [
        {
          object_name: index === 0 ? 'Mars' : 'Venus',
          aspect: index === 0 ? 'Square' : 'Trine',
          aspect_degrees: index === 0 ? 90 : 120,
          orb: 0.24 + index / 100,
          allowed_orb: 2.29,
          strength: 0.91 - index / 100,
        },
      ],
    }));
    astroClockApiMock.getDegreeHitPoints.mockResolvedValueOnce({
      success: true,
      data: {
        points_catalog_version: 'filtered-test',
        computed_count: 403,
        active_count: 21,
        unavailable_count: 0,
        top_hits: topHits,
        unavailable: [],
      },
    });

    render(
      <DegreeHitsTile
        metrics={{ degree_hits: { items: [] } }}
        specialDegrees={[]}
        onApplyDegrees={() => {}}
        onClearDegrees={() => {}}
        pointsContext={{
          mode: 'manual',
          datetime: '2026-03-22T06:32:00',
          location: 'Israel',
          timezone: 'Asia/Jerusalem',
          latitude: 31.778,
          longitude: 35.235,
          houseSystem: 'R',
        }}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'More' }));

    const dialog = await screen.findByRole('dialog', { name: 'Degree Hits Details' });
    await waitFor(() => expect(astroClockApiMock.getDegreeHitPoints).toHaveBeenCalledWith(expect.objectContaining({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      houseSystem: 'P',
    })));

    expect(within(dialog).getByText('Top 10 active symbolic points')).toBeTruthy();
    expect(within(dialog).queryByText(/not predictions, diagnoses, accusations, or proof/i)).toBeNull();
    expect(within(dialog).getAllByTestId('degree-hit-point-row')).toHaveLength(10);
    expect(within(dialog).getByText('Theft').closest('[data-testid="degree-hit-point-row"]').className).toContain('border-red');
    expect(within(dialog).getByText('Mars square')).toBeTruthy();
    expect(within(dialog).getByText(/0\.24/)).toBeTruthy();
    expect(within(dialog).queryByText(/caution/i)).toBeNull();
    expect(dialog.textContent).not.toMatch(/parts#|midpoints#|formula|catalog_source|filtered catalog/i);

    const header = screen.getByText('Degree Analysis').parentElement.parentElement;
    expect(within(header).queryByText(/caution/i)).toBeNull();
    expect(within(header).queryByText(/^\d+ active$/i)).toBeNull();
  });

  it('uses the premium gate for More without loading point details', () => {
    const onDetailsLocked = vi.fn();

    render(
      <DegreeHitsTile
        metrics={{ degree_hits: { items: [] } }}
        specialDegrees={[]}
        onApplyDegrees={() => {}}
        onClearDegrees={() => {}}
        pointsContext={{ mode: 'manual' }}
        detailsLocked
        detailsLockedTitle="Premium feature - unlock Vox Stella to use this workflow"
        onDetailsLocked={onDetailsLocked}
      />
    );

    const moreButton = screen.getByRole('button', { name: 'More' });
    expect(moreButton).toHaveAttribute('title', 'Premium feature - unlock Vox Stella to use this workflow');
    expect(moreButton.className).toContain('border-red');

    fireEvent.click(moreButton);

    expect(onDetailsLocked).toHaveBeenCalledTimes(1);
    expect(astroClockApiMock.getDegreeHitPoints).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog', { name: 'Degree Hits Details' })).toBeNull();
  });

  it('fetches fresh symbolic points every time More opens', async () => {
    astroClockApiMock.getDegreeHitPoints
      .mockResolvedValueOnce({
        success: true,
        data: {
          top_hits: [{
            key: 'old',
            name: 'Old Point',
            zodiac: { formatted: '1 Aries 00' },
            point_score: 1,
            ui_severity: 'neutral',
            ui_color: 'slate',
            hits: [{ object_name: 'Sun', aspect: 'Conjunction', orb: 0.1, allowed_orb: 2.7, strength: 0.9 }],
          }],
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          top_hits: [{
            key: 'new',
            name: 'New Point',
            zodiac: { formatted: '2 Taurus 00' },
            point_score: 1.2,
            ui_severity: 'neutral',
            ui_color: 'slate',
            hits: [{ object_name: 'Moon', aspect: 'Sextile', orb: 0.2, allowed_orb: 2.5, strength: 0.8 }],
          }],
        },
      });

    render(
      <DegreeHitsTile
        metrics={{ degree_hits: { items: [] } }}
        specialDegrees={[]}
        onApplyDegrees={() => {}}
        onClearDegrees={() => {}}
        pointsContext={{
          mode: 'manual',
          datetime: '2026-03-22T06:32:00',
          location: 'Israel',
          timezone: 'Asia/Jerusalem',
          houseSystem: 'R',
        }}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'More' }));
    const firstDialog = await screen.findByRole('dialog', { name: 'Degree Hits Details' });
    await waitFor(() => expect(within(firstDialog).getByText('Old Point')).toBeTruthy());

    fireEvent.click(within(firstDialog).getByRole('button', { name: 'Close' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Degree Hits Details' })).toBeNull());

    fireEvent.click(screen.getByRole('button', { name: 'More' }));
    const secondDialog = await screen.findByRole('dialog', { name: 'Degree Hits Details' });

    await waitFor(() => expect(astroClockApiMock.getDegreeHitPoints).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(within(secondDialog).getByText('New Point')).toBeTruthy());
    expect(within(secondDialog).queryByText('Old Point')).toBeNull();
  });
});
