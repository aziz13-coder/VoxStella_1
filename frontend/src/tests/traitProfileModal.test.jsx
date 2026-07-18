import React from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import TraitProfileModal from '../features/astroclock/TraitProfileModal.jsx';
import { buildProfessionSuggestions } from '../features/astroclock/knowledgeMap.mjs';

const astroClockApiMock = vi.hoisted(() => ({
  getTraitProfile: vi.fn(),
  getDegreeHitPoints: vi.fn(),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: astroClockApiMock,
}));

describe('TraitProfileModal layout', () => {
  beforeEach(() => {
    astroClockApiMock.getTraitProfile.mockReset();
    astroClockApiMock.getDegreeHitPoints.mockReset();
    astroClockApiMock.getDegreeHitPoints.mockResolvedValue({
      success: true,
      data: { chart_meta: {}, points: [] },
    });
    astroClockApiMock.getTraitProfile.mockResolvedValue({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        receptions: null,
        house_influences: {
          houses: [
            {
              house: 1,
              sign: 'Pisces',
              influences: [
                {
                  planet: 'Mars',
                  type: 'occupation',
                  value: 60.24,
                  rank: 'dominant',
                  keywords: ['support', 'governance', 'dispositorship'],
                  details: { breakdown: null },
                },
              ],
            },
            {
              house: 2,
              sign: 'Taurus',
              influences: [
                {
                  planet: 'Moon',
                  type: 'aspect',
                  aspect: 'Conjunction',
                  value: 44.77,
                  rank: 'secondary',
                  keywords: ['support'],
                  details: { breakdown: null },
                },
              ],
            },
          ],
        },
      },
    });
  });

  it('adds Points as a Trait Profile tab before All Traits and renders point rows there', async () => {
    const topHits = [
      {
        key: 'career',
        name: 'Career',
        available: true,
        longitude: 123.45,
        zodiac: { formatted: '3 Leo 27' },
        score: 1.253,
        point_score: 1.253,
        ui_severity: 'supportive',
        hits: [
          {
            object_name: 'Jupiter',
            aspect: 'Trine',
            aspect_degrees: 120,
            orb: 0.42,
            allowed_orb: 2.5,
            strength: 0.832,
          },
        ],
      },
      {
        key: 'mercury_saturn',
        name: 'Disciplined Thought',
        available: true,
        longitude: 210.0,
        zodiac: { formatted: '0 Scorpio 00' },
        score: 0.995,
        point_score: 0.995,
        ui_severity: 'neutral',
        hits: [
          {
            object_name: 'Mercury',
            aspect: 'Conjunction',
            aspect_degrees: 0,
            orb: 2.17,
            allowed_orb: 3.71,
            strength: 0.415,
          },
          {
            object_name: 'Saturn',
            aspect: 'Conjunction',
            aspect_degrees: 0,
            orb: 2.17,
            allowed_orb: 3.35,
            strength: 0.353,
          },
          {
            object_name: 'Neptune',
            aspect: 'Conjunction',
            aspect_degrees: 0,
            orb: 2.44,
            allowed_orb: 3.16,
            strength: 0.227,
          },
        ],
      },
      ...Array.from({ length: 9 }, (_, index) => ({
        key: `active_point_${index + 1}`,
        name: `Active Point ${index + 1}`,
        available: true,
        longitude: 220 + index,
        zodiac: { formatted: `${index + 1} Scorpio 00` },
        score: 0.9 - index * 0.04,
        point_score: 0.9 - index * 0.04,
        ui_severity: 'neutral',
        hits: [
          {
            object_name: 'Venus',
            aspect: 'Sextile',
            aspect_degrees: 60,
            orb: 0.5 + index / 10,
            allowed_orb: 2.5,
            strength: 0.8 - index / 20,
          },
        ],
      })),
    ];
    astroClockApiMock.getDegreeHitPoints.mockResolvedValue({
      success: true,
      data: {
        chart_meta: {
          datetime_utc: '2026-03-22T04:32:00Z',
          latitude: 31.778,
          longitude: 35.235,
          house_system: 'R',
          precision: { has_exact_time: true, has_houses: true, has_manager_table: true },
        },
        top_hits: topHits,
        active_count: 11,
        points: [
          {
            key: 'destroyer_violence',
            name: 'Destroyer, violence',
            available: false,
            longitude: null,
            zodiac: null,
            score: 0,
            formula: { summary: 'Asc + Moon/Manager(1st cusp) exchange', used: 'day' },
            hits: [],
            unavailable_reasons: [{ code: 'manager_missing', message: 'manager object unavailable' }],
          },
        ],
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByRole('button', { name: 'Points' });
    const tabLabels = screen.getAllByRole('button').map((button) => button.textContent);
    expect(tabLabels.indexOf('Points')).toBeGreaterThan(-1);
    expect(tabLabels.indexOf('Points')).toBeLessThan(tabLabels.indexOf('All Traits'));

    fireEvent.click(screen.getByRole('button', { name: 'Points' }));

    await waitFor(() => expect(astroClockApiMock.getDegreeHitPoints).toHaveBeenCalledWith(expect.objectContaining({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'P',
      sexCode: '0',
    })));

    expect(screen.queryByText('Point Activations')).toBeNull();
    expect(screen.queryByText('Tracked Points')).toBeNull();
    expect(screen.queryByText('Modern unavailable')).toBeNull();
    expect(screen.queryByText('Modern included')).toBeNull();
    expect(screen.getByText('Active Points')).toBeTruthy();
    expect(screen.getAllByTestId('trait-point-row')).toHaveLength(10);
    expect(screen.getAllByText('Career').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('trine Jupiter').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Disciplined Thought')).toHaveLength(1);
    expect(screen.getByText('conjunction Mercury')).toBeTruthy();
    expect(screen.getByText('conjunction Saturn')).toBeTruthy();
    expect(screen.getByText('conjunction Neptune')).toBeTruthy();
    expect(screen.queryByText('Active Point 9')).toBeNull();
    expect(screen.queryByText('Destroyer, violence')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Female' }));
    await waitFor(() => expect(astroClockApiMock.getDegreeHitPoints).toHaveBeenLastCalledWith(expect.objectContaining({
      sexCode: '2',
      houseSystem: 'P',
    })));
    expect(document.body.textContent).not.toMatch(/Formula|Asc \+ Manager|Mercury-Saturn midpoint/i);
    expect(document.body.textContent).not.toMatch(/parts#|midpoints#|research row|module|family score|serial_homicide|cult_mass_spree|individual_homicide|legal_research_mixed/i);
  });

  it('uses the wider responsive modal and house influence grid', async () => {
    const { container } = render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('House Influence');
    fireEvent.click(screen.getByRole('button', { name: 'House Influence' }));

    expect(container.querySelector('.max-w-6xl')).toBeTruthy();

    const houseGrid = Array.from(container.querySelectorAll('.grid'))
      .find((el) => el.className.includes('md:grid-cols-2') && el.className.includes('xl:grid-cols-3'));
    expect(houseGrid).toBeTruthy();
    expect(houseGrid.className).toContain('md:grid-cols-2');
    expect(houseGrid.className).toContain('xl:grid-cols-3');
    expect(houseGrid.className).not.toContain('lg:grid-cols-3');
  });

  it('renders house influence keywords in a separate row below the meter controls', async () => {
    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('House Influence');
    fireEvent.click(screen.getByRole('button', { name: 'House Influence' }));

    const keywordChip = screen.getByText('dispositorship');
    const keywordRow = keywordChip.closest('div');
    expect(keywordRow).toBeTruthy();
    expect(keywordRow.className).toContain('flex-wrap');

    const mainRow = keywordRow.previousElementSibling;
    expect(mainRow).toBeTruthy();
    expect(within(mainRow).getByRole('button', { name: 'Details' })).toBeTruthy();
  });

  it('lets users choose a saved snap as the trait chart source', async () => {
    const snap = {
      id: 'snap-1',
      label: 'Greenwich snap',
      effective_datetime: '2026-05-05T10:45:00+00:00',
      location: 'Greenwich, UK',
      special_degrees: ['Regulus'],
      dashboard: {
        timezone: 'Europe/London',
        latitude: 51.4769,
        longitude: -0.0005,
      },
    };

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
        snaps={[snap]}
        snapsLoaded
      />
    );

    await waitFor(() => expect(astroClockApiMock.getTraitProfile).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByLabelText('Saved snap'), { target: { value: 'snap-1' } });

    await waitFor(() => expect(astroClockApiMock.getTraitProfile).toHaveBeenCalledTimes(2));
    const latestRequest = astroClockApiMock.getTraitProfile.mock.calls.at(-1)[0];
    expect(latestRequest).toMatchObject({
      snapId: 'snap-1',
      houseSystem: 'R',
      specialDegrees: ['Regulus'],
    });
    expect(latestRequest).not.toHaveProperty('mode');
    expect(latestRequest).not.toHaveProperty('datetime');
    expect(latestRequest).not.toHaveProperty('location');
    expect(latestRequest).not.toHaveProperty('timezone');
    expect(latestRequest).not.toHaveProperty('latitude');
    expect(latestRequest).not.toHaveProperty('longitude');

    fireEvent.click(screen.getByRole('button', { name: 'Points' }));
    await waitFor(() => expect(astroClockApiMock.getDegreeHitPoints).toHaveBeenCalledTimes(1));
    const pointsRequest = astroClockApiMock.getDegreeHitPoints.mock.calls.at(-1)[0];
    expect(pointsRequest).toMatchObject({
      snapId: 'snap-1',
      houseSystem: 'P',
      sexCode: '0',
    });
    expect(pointsRequest).not.toHaveProperty('mode');
    expect(pointsRequest).not.toHaveProperty('datetime');
    expect(pointsRequest).not.toHaveProperty('location');
    expect(pointsRequest).not.toHaveProperty('timezone');
    expect(pointsRequest).not.toHaveProperty('latitude');
    expect(pointsRequest).not.toHaveProperty('longitude');
  });

  it('disables review-required and superseded saved charts as trait sources', async () => {
    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
        snaps={[
          {
            id: 'snap-safe',
            label: 'Safe chart',
            effective_datetime: '2002-04-05T09:20:00+00:00',
            location: 'Synthetic place',
          },
          {
            id: 'snap-review',
            label: 'Review chart',
            calculation_context: { review_required: true },
          },
          {
            id: 'snap-old',
            label: 'Old chart',
            superseded_by: 'snap-safe',
          },
        ]}
        snapsLoaded
      />
    );

    await waitFor(() => expect(astroClockApiMock.getTraitProfile).toHaveBeenCalledTimes(1));
    const select = screen.getByLabelText('Saved snap');
    expect(within(select).getByRole('option', { name: /Review chart.*needs context review/i })).toBeDisabled();
    expect(within(select).getByRole('option', { name: /Old chart.*superseded.*corrected copy/i })).toBeDisabled();
    expect(screen.getByText(/Review-required and superseded saved charts are disabled/i)).toBeInTheDocument();
  });

  it('passes current chart coordinates in trait profile requests', async () => {
    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        latitude={31.778}
        longitude={35.235}
        houseSystem="R"
        fixedStarHits={[]}
        snaps={[]}
      />
    );

    await waitFor(() => expect(astroClockApiMock.getTraitProfile).toHaveBeenCalledTimes(1));
    expect(astroClockApiMock.getTraitProfile.mock.calls[0][0]).toMatchObject({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });
  });

  it('copies chart context and astrological factors into the AI prompt', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={['25 Leo']}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        chartSnapshot={{
          timestamp: '2026-03-22T06:32:00Z',
          location: 'Israel',
          timezone: 'Asia/Jerusalem',
          timezone_label: 'Asia/Jerusalem (UTC+02:00)',
          ascendant: 18.9,
          midheaven: 271.5,
          planets: [
            { planet: 'Sun', sign: 'Aries', house: 1, longitude: 1.5, dignity_score: 2, essential_dignity: 0, accidental_dignity: 2, retrograde: false },
          ],
          solar_conditions: { combustion: [{ planet: 'Mercury', distance_from_sun: 2.1 }] },
          top_aspects: [{ planet1: 'Sun', planet2: 'Moon', aspect: 'Conjunction', orb: 0.4 }],
          morin_aspects: [{ planet1: 'Mercury', planet2: 'Jupiter', aspect: 'Sextile', orb: 0.8 }],
          house_cusps: [18.9, 44.0, 71.0],
          house_rulers: { 1: 'Mars' },
          receptions: { traditional_reception: { label: 'Mixed reception' }, mutual: [{ p1: 'Venus', p2: 'Mars' }], top_unilateral: [] },
          fixed_star_hits: [{ star: 'Regulus', planet: 'Sun' }],
        }}
        fixedStarHits={[{ star: 'Regulus', planet: 'Sun' }]}
      />
    );

    const copyButton = await screen.findByRole('button', { name: 'Copy AI Prompt' });
    fireEvent.click(copyButton);

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const copied = String(writeText.mock.calls[0][0] || '');
    expect(copied).toContain('"chart_context"');
    expect(copied).toContain('"location": "Israel"');
    expect(copied).toContain('"solar_conditions"');
    expect(copied).toContain('"house_cusps"');
    expect(copied).toContain('"fixed_star_hits"');
    expect(copied).toContain('"selected_domains"');
  });

  it('shows neutral traits alongside positive and negative splits', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        receptions: null,
        traits: [
          { id: 'generosity', name: 'Generosity', score: 82, raw_score: 41, max_score: 50, support_hits: 4, support_total: 5, band: 'strong', polarity: 'positive', domain: 'ethic_prosocial', keywords: ['friends'] },
          { id: 'self_assertion', name: 'Self-assertion', score: 76, raw_score: 19, max_score: 25, support_hits: 2, support_total: 3, band: 'strong', polarity: 'neutral', domain: 'drive', keywords: ['life'], family_representative: true, family_size: 2, related_traits: [{ id: 'warlike', name: 'Warlike', polarity: 'neutral', score: 76 }] },
          { id: 'warlike', name: 'Warlike', score: 76, raw_score: 19, max_score: 25, support_hits: 2, support_total: 3, band: 'strong', polarity: 'neutral', domain: 'drive_assertion', keywords: ['life'], family_representative: false, family_size: 2, related_traits: [] },
          { id: 'rashness', name: 'Rashness', score: 64, raw_score: 16, max_score: 25, support_hits: 2, support_total: 4, band: 'likely', polarity: 'negative', domain: 'drive', keywords: ['life'] },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Style');
    expect(screen.getByText('Top Constructive')).toBeTruthy();
    expect(screen.getByText('Top Style')).toBeTruthy();
    expect(screen.getByText('Top Strain')).toBeTruthy();
    expect(screen.getAllByText('Self-assertion').length).toBeGreaterThan(0);
    expect(screen.getAllByText('1 related variants').length).toBeGreaterThan(0);

    const polaritySelect = screen.getByLabelText('Polarity');
    expect(polaritySelect.querySelector('option[value="neutral"]')).toBeTruthy();
  });

  it('shows neutral and negative summary panels even when backend top_traits are all positive', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [
          { id: 'positive_trait', name: 'Positive Trait', score: 90, raw_score: 18, max_score: 20, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'social_function', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, keywords: ['friends'] },
        ],
        summary_traits: [
          { id: 'positive_trait', name: 'Positive Trait', score: 90, raw_score: 18, max_score: 20, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'social_function', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['friends'] },
          { id: 'neutral_trait', name: 'Neutral Trait', score: 72, raw_score: 18, max_score: 25, support_hits: 2, support_total: 3, band: 'likely', polarity: 'neutral', domain: 'drive', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['life'] },
          { id: 'negative_trait', name: 'Negative Trait', score: 61, raw_score: 11, max_score: 18, support_hits: 1, support_total: 2, band: 'likely', polarity: 'negative', domain: 'temperament_negative', source_status: 'curated', provisional: false, summary_surface: 'caution', summary_eligible: true, summary_priority: 0, keywords: ['delay'] },
        ],
        top_traits_by_polarity: {
          positive: [{ id: 'positive_trait', name: 'Positive Trait', score: 90, raw_score: 18, max_score: 20, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'social_function', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['friends'] }],
          neutral: [{ id: 'neutral_trait', name: 'Neutral Trait', score: 72, raw_score: 18, max_score: 25, support_hits: 2, support_total: 3, band: 'likely', polarity: 'neutral', domain: 'drive', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['life'] }],
          negative: [{ id: 'negative_trait', name: 'Negative Trait', score: 61, raw_score: 11, max_score: 18, support_hits: 1, support_total: 2, band: 'likely', polarity: 'negative', domain: 'temperament_negative', source_status: 'curated', provisional: false, summary_surface: 'caution', summary_eligible: true, summary_priority: 0, keywords: ['delay'] }],
        },
        receptions: null,
        traits: [
          { id: 'positive_trait', name: 'Positive Trait', score: 90, raw_score: 18, max_score: 20, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'social_function', source_status: 'curated', provisional: false, family_representative: true, summary_surface: 'general', summary_eligible: true, keywords: ['friends'] },
          { id: 'neutral_trait', name: 'Neutral Trait', score: 72, raw_score: 18, max_score: 25, support_hits: 2, support_total: 3, band: 'likely', polarity: 'neutral', domain: 'drive', source_status: 'curated', provisional: false, family_representative: true, summary_surface: 'general', summary_eligible: true, keywords: ['life'] },
          { id: 'negative_trait', name: 'Negative Trait', score: 61, raw_score: 11, max_score: 18, support_hits: 1, support_total: 2, band: 'likely', polarity: 'negative', domain: 'temperament_negative', source_status: 'curated', provisional: false, family_representative: true, summary_surface: 'caution', summary_eligible: true, keywords: ['delay'] },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Style');

    const topNeutral = screen.getByText('Top Style').closest('div.border');
    const topNegative = screen.getByText('Top Strain').closest('div.border');
    expect(topNeutral.textContent).toContain('Neutral Trait');
    expect(topNegative.textContent).toContain('Negative Trait');
  });

  it('suppresses provisional traits from summary splits when curated alternatives exist but keeps them visible in the full list', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        receptions: null,
        traits: [
          { id: 'curated_positive', name: 'Curated Positive', score: 80, raw_score: 16, max_score: 20, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'drive', family_representative: true, family_size: 1, related_traits: [], source_status: 'curated', provisional: false, keywords: ['life'] },
          { id: 'provisional_positive', name: 'Provisional Positive', score: 78, raw_score: 14, max_score: 18, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'drive', family_representative: true, family_size: 1, related_traits: [], source_status: 'provisional', provisional: true, keywords: ['life'] },
          { id: 'curated_neutral', name: 'Curated Neutral', score: 70, raw_score: 14, max_score: 20, support_hits: 2, support_total: 3, band: 'likely', polarity: 'neutral', domain: 'temperament', family_representative: true, family_size: 1, related_traits: [], source_status: 'curated', provisional: false, keywords: ['temperament'] },
          { id: 'provisional_negative', name: 'Provisional Negative', score: 62, raw_score: 12, max_score: 19, support_hits: 1, support_total: 2, band: 'likely', polarity: 'negative', domain: 'health', family_representative: true, family_size: 1, related_traits: [], source_status: 'provisional', provisional: true, keywords: ['illness'] },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Constructive');

    const topPositive = screen.getByText('Top Constructive').closest('div.border');
    const topNeutral = screen.getByText('Top Style').closest('div.border');
    const topNegative = screen.getByText('Top Strain').closest('div.border');

    expect(topPositive.textContent).toContain('Curated Positive');
    expect(topPositive.textContent).not.toContain('Provisional Positive');
    expect(topNeutral.textContent).toContain('Curated Neutral');
    expect(topNegative.textContent).toContain('No results');

    fireEvent.click(screen.getByRole('button', { name: 'All Traits' }));
    expect(screen.getByText('Provisional Positive')).toBeTruthy();
    expect(screen.getByText('Provisional Negative')).toBeTruthy();
    expect(screen.queryByText('Provisional source')).toBeNull();
  });

  it('suppresses summary-ineligible specialized traits from the top split while keeping them in the full list', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [
          { id: 'general_trait', name: 'General Trait', score: 88, raw_score: 22, max_score: 25, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'cognitive_style', family_representative: true, family_size: 1, related_traits: [], source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, keywords: ['mind'] },
        ],
        receptions: null,
        traits: [
          { id: 'general_trait', name: 'General Trait', score: 88, raw_score: 22, max_score: 25, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'cognitive_style', family_representative: true, family_size: 1, related_traits: [], source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, keywords: ['mind'] },
          { id: 'specialized_indicator', name: 'Specialized Indicator', score: 100, raw_score: 20, max_score: 20, support_hits: 2, support_total: 2, band: 'strong', polarity: 'negative', domain: 'disease_infectious', family_representative: true, family_size: 1, related_traits: [], source_status: 'curated', provisional: false, summary_surface: 'specialized', summary_eligible: false, keywords: ['illness'] },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Constructive');

    const topPositive = screen.getByText('Top Constructive').closest('div.border');
    const topNegative = screen.getByText('Top Strain').closest('div.border');

    expect(topPositive.textContent).toContain('General Trait');
    expect(topNegative.textContent).toContain('No results');
    fireEvent.click(screen.getByRole('button', { name: 'All Traits' }));
    expect(screen.getByText('Specialized Indicator')).toBeTruthy();
  });

  it('applies band and domain filters to backend polarity summaries', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        summary_traits: [
          { id: 'positive_strong', name: 'Positive Strong', score: 88, raw_score: 22, max_score: 25, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'cognition', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['mind'] },
          { id: 'neutral_likely', name: 'Neutral Likely', score: 70, raw_score: 14, max_score: 20, support_hits: 2, support_total: 3, band: 'likely', polarity: 'neutral', domain: 'drive', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['life'] },
          { id: 'negative_strong', name: 'Negative Strong', score: 77, raw_score: 17, max_score: 22, support_hits: 2, support_total: 2, band: 'strong', polarity: 'negative', domain: 'temperament_negative', source_status: 'curated', provisional: false, summary_surface: 'caution', summary_eligible: true, summary_priority: 0, keywords: ['delay'] },
        ],
        top_traits_by_polarity: {
          positive: [{ id: 'positive_strong', name: 'Positive Strong', score: 88, raw_score: 22, max_score: 25, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'cognition', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['mind'] }],
          neutral: [{ id: 'neutral_likely', name: 'Neutral Likely', score: 70, raw_score: 14, max_score: 20, support_hits: 2, support_total: 3, band: 'likely', polarity: 'neutral', domain: 'drive', source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['life'] }],
          negative: [{ id: 'negative_strong', name: 'Negative Strong', score: 77, raw_score: 17, max_score: 22, support_hits: 2, support_total: 2, band: 'strong', polarity: 'negative', domain: 'temperament_negative', source_status: 'curated', provisional: false, summary_surface: 'caution', summary_eligible: true, summary_priority: 0, keywords: ['delay'] }],
        },
        receptions: null,
        traits: [
          { id: 'positive_strong', name: 'Positive Strong', score: 88, raw_score: 22, max_score: 25, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'cognition', family_representative: true, source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['mind'] },
          { id: 'neutral_likely', name: 'Neutral Likely', score: 70, raw_score: 14, max_score: 20, support_hits: 2, support_total: 3, band: 'likely', polarity: 'neutral', domain: 'drive', family_representative: true, source_status: 'curated', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['life'] },
          { id: 'negative_strong', name: 'Negative Strong', score: 77, raw_score: 17, max_score: 22, support_hits: 2, support_total: 2, band: 'strong', polarity: 'negative', domain: 'temperament_negative', family_representative: true, source_status: 'curated', provisional: false, summary_surface: 'caution', summary_eligible: true, summary_priority: 0, keywords: ['delay'] },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Style');

    fireEvent.change(screen.getByLabelText('Band'), { target: { value: 'strong' } });

    let topPositive = screen.getByText('Top Constructive').closest('div.border');
    let topNeutral = screen.getByText('Top Style').closest('div.border');
    let topNegative = screen.getByText('Top Strain').closest('div.border');

    expect(topPositive.textContent).toContain('Positive Strong');
    expect(topNeutral.textContent).toContain('No results');
    expect(topNegative.textContent).toContain('Negative Strong');

    fireEvent.change(screen.getByLabelText('Band'), { target: { value: 'all' } });
    fireEvent.click(screen.getByRole('button', { name: /Domains \(/ }));
    fireEvent.click(screen.getByLabelText('Select all'));
    fireEvent.click(screen.getByLabelText('drive'));

    topPositive = screen.getByText('Top Constructive').closest('div.border');
    topNeutral = screen.getByText('Top Style').closest('div.border');
    topNegative = screen.getByText('Top Strain').closest('div.border');

    expect(topPositive.textContent).toContain('No results');
    expect(topNeutral.textContent).toContain('Neutral Likely');
    expect(topNegative.textContent).toContain('No results');
  });

  it('keeps source lineage labels out of the visible trait profile', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [
          { id: 'carter_trait', name: 'Carter Trait', score: 88, raw_score: 22, max_score: 25, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'social_function', family_representative: true, source_status: 'curated', source_lineage: 'carter', source_lineage_label: 'Carter-derived', provisional: false, summary_surface: 'general', summary_eligible: true, keywords: ['friends'] },
        ],
        receptions: null,
        traits: [
          { id: 'carter_trait', name: 'Carter Trait', score: 88, raw_score: 22, max_score: 25, support_hits: 2, support_total: 2, band: 'strong', polarity: 'positive', domain: 'social_function', family_representative: true, source_status: 'curated', source_lineage: 'carter', source_lineage_label: 'Carter-derived', provisional: false, summary_surface: 'general', summary_eligible: true, keywords: ['friends'] },
          { id: 'classical_trait', name: 'Classical Trait', score: 72, raw_score: 18, max_score: 25, support_hits: 2, support_total: 3, band: 'likely', polarity: 'positive', domain: 'cognitive_style', family_representative: true, source_status: 'curated', source_lineage: 'classical', source_lineage_label: 'Classical source', provisional: false, summary_surface: 'general', summary_eligible: true, keywords: ['mind'] },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Constructive');
    expect(screen.getByText('Carter Trait')).toBeTruthy();
    expect(screen.queryByText('Carter-derived')).toBeNull();
    expect(screen.queryByText('Classical source')).toBeNull();
  });

  it('does not render source layers or corpus citations in visible trait cards', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        trait_enrichment_meta: { morin_keywords_policy: 'canonical_non_scoring', version: 1 },
        receptions: null,
        traits: [
          {
            id: 'scholarship',
            name: 'Scholarship',
            score: 84,
            raw_score: 21,
            max_score: 25,
            support_hits: 2,
            support_total: 2,
            band: 'strong',
            polarity: 'positive',
            domain: 'cognitive_style',
            family_representative: true,
            source_status: 'curated',
            source_lineage: 'carter',
            source_lineage_label: 'Carter-derived',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            keywords: ['learning', 'speech'],
            keyword_layers: {
              morin: ['learning', 'speech'],
              classical: ['study', 'judgment'],
              modern: ['meaning-making'],
            },
            citation_summary: { count: 2, lineages: ['classical', 'modern'], top_source: 'Demetra George' },
            citations: [
              {
                citation_id: 'demetra:chunk-1',
                source_lineage: 'classical',
                source_label: 'Demetra George',
                excerpt: 'Scholarship depends on Mercury and disciplined inquiry.',
              },
              {
                citation_id: 'rudhyar:chunk-2',
                source_lineage: 'modern',
                source_label: 'Dane Rudhyar',
                excerpt: 'Mental development shapes the person-centered life pattern.',
              },
            ],
          },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('All Traits');
    expect(screen.getByText('Scholarship')).toBeTruthy();
    expect(screen.queryByText('Source Layers')).toBeNull();
    expect(screen.queryByText('Corpus Citations')).toBeNull();
    expect(screen.queryByText('Carter-derived')).toBeNull();
    expect(screen.queryByText(/Scholarship depends on Mercury/)).toBeNull();
    expect(screen.queryByText(/Mental development shapes the person-centered life pattern/)).toBeNull();
  });

  it('does not expose source filtering in the visible filter bar', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        summary_traits: [
          {
            id: 'carter_trait',
            name: 'Carter Trait',
            score: 80,
            raw_score: 16,
            max_score: 20,
            support_hits: 2,
            support_total: 2,
            band: 'strong',
            polarity: 'positive',
            domain: 'social_function',
            source_status: 'curated',
            source_lineage: 'carter',
            source_lineage_label: 'Carter-derived',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['friends'],
            keyword_layers: { morin: ['friends'] },
            citations: [],
          },
          {
            id: 'modern_backed_trait',
            name: 'Modern-backed Trait',
            score: 74,
            raw_score: 18,
            max_score: 24,
            support_hits: 2,
            support_total: 3,
            band: 'likely',
            polarity: 'positive',
            domain: 'cognitive_style',
            source_status: 'curated',
            source_lineage: 'carter',
            source_lineage_label: 'Carter-derived',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['learning'],
            keyword_layers: { morin: ['learning'], modern: ['meaning-making'] },
            citations: [{ citation_id: 'rudhyar:chunk-2', source_lineage: 'modern', source_label: 'Dane Rudhyar', excerpt: 'Meaning-making is central here.' }],
          },
        ],
        top_traits_by_polarity: {
          positive: [
            {
              id: 'carter_trait',
              name: 'Carter Trait',
              score: 80,
              raw_score: 16,
              max_score: 20,
              support_hits: 2,
              support_total: 2,
              band: 'strong',
              polarity: 'positive',
              domain: 'social_function',
              source_status: 'curated',
              source_lineage: 'carter',
              source_lineage_label: 'Carter-derived',
              provisional: false,
              summary_surface: 'general',
              summary_eligible: true,
              summary_priority: 0,
              keywords: ['friends'],
              keyword_layers: { morin: ['friends'] },
              citations: [],
            },
            {
              id: 'modern_backed_trait',
              name: 'Modern-backed Trait',
              score: 74,
              raw_score: 18,
              max_score: 24,
              support_hits: 2,
              support_total: 3,
              band: 'likely',
              polarity: 'positive',
              domain: 'cognitive_style',
              source_status: 'curated',
              source_lineage: 'carter',
              source_lineage_label: 'Carter-derived',
              provisional: false,
              summary_surface: 'general',
              summary_eligible: true,
              summary_priority: 0,
              keywords: ['learning'],
              keyword_layers: { morin: ['learning'], modern: ['meaning-making'] },
              citations: [{ citation_id: 'rudhyar:chunk-2', source_lineage: 'modern', source_label: 'Dane Rudhyar', excerpt: 'Meaning-making is central here.' }],
            },
          ],
          neutral: [],
          negative: [],
        },
        receptions: null,
        traits: [
          {
            id: 'carter_trait',
            name: 'Carter Trait',
            score: 80,
            raw_score: 16,
            max_score: 20,
            support_hits: 2,
            support_total: 2,
            band: 'strong',
            polarity: 'positive',
            domain: 'social_function',
            family_representative: true,
            source_status: 'curated',
            source_lineage: 'carter',
            source_lineage_label: 'Carter-derived',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['friends'],
            keyword_layers: { morin: ['friends'] },
            citations: [],
          },
          {
            id: 'modern_backed_trait',
            name: 'Modern-backed Trait',
            score: 74,
            raw_score: 18,
            max_score: 24,
            support_hits: 2,
            support_total: 3,
            band: 'likely',
            polarity: 'positive',
            domain: 'cognitive_style',
            family_representative: true,
            source_status: 'curated',
            source_lineage: 'carter',
            source_lineage_label: 'Carter-derived',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['learning'],
            keyword_layers: { morin: ['learning'], modern: ['meaning-making'] },
            citations: [{ citation_id: 'rudhyar:chunk-2', source_lineage: 'modern', source_label: 'Dane Rudhyar', excerpt: 'Meaning-making is central here.' }],
          },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Constructive');
    expect(screen.queryByLabelText('Source')).toBeNull();

    const topPositive = screen.getByText('Top Constructive').closest('div.border');
    expect(topPositive.textContent).toContain('Modern-backed Trait');
    expect(topPositive.textContent).toContain('Carter Trait');
  });

  it('shows an explicit empty-state notice when strength and domain filters intersect to zero results and can reset them', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        summary_traits: [
          {
            id: 'classical_trait',
            name: 'Classical Trait',
            score: 82,
            raw_score: 18,
            max_score: 22,
            support_hits: 2,
            support_total: 2,
            band: 'strong',
            polarity: 'positive',
            domain: 'cognitive_style',
            source_status: 'curated',
            source_lineage: 'classical',
            source_lineage_label: 'Classical source',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['mind'],
            keyword_layers: { morin: ['mind'], classical: ['study'] },
            citations: [{ citation_id: 'demetra:1', source_lineage: 'classical', source_label: 'Demetra George', excerpt: 'Study and judgment.' }],
          },
          {
            id: 'social_trait',
            name: 'Social Trait',
            score: 75,
            raw_score: 15,
            max_score: 20,
            support_hits: 2,
            support_total: 2,
            band: 'strong',
            polarity: 'positive',
            domain: 'social_function',
            source_status: 'curated',
            source_lineage: 'carter',
            source_lineage_label: 'Carter-derived',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['friends'],
            keyword_layers: { morin: ['friends'] },
            citations: [],
          },
        ],
        top_traits_by_polarity: {
          positive: [
            {
              id: 'classical_trait',
              name: 'Classical Trait',
              score: 82,
              raw_score: 18,
              max_score: 22,
              support_hits: 2,
              support_total: 2,
              band: 'strong',
              polarity: 'positive',
              domain: 'cognitive_style',
              source_status: 'curated',
              source_lineage: 'classical',
              source_lineage_label: 'Classical source',
              provisional: false,
              summary_surface: 'general',
              summary_eligible: true,
              summary_priority: 0,
              keywords: ['mind'],
              keyword_layers: { morin: ['mind'], classical: ['study'] },
              citations: [{ citation_id: 'demetra:1', source_lineage: 'classical', source_label: 'Demetra George', excerpt: 'Study and judgment.' }],
            },
            {
              id: 'social_trait',
              name: 'Social Trait',
              score: 75,
              raw_score: 15,
              max_score: 20,
              support_hits: 2,
              support_total: 2,
              band: 'strong',
              polarity: 'positive',
              domain: 'social_function',
              source_status: 'curated',
              source_lineage: 'carter',
              source_lineage_label: 'Carter-derived',
              provisional: false,
              summary_surface: 'general',
              summary_eligible: true,
              summary_priority: 0,
              keywords: ['friends'],
              keyword_layers: { morin: ['friends'] },
              citations: [],
            },
          ],
          neutral: [],
          negative: [],
        },
        receptions: null,
        traits: [
          {
            id: 'classical_trait',
            name: 'Classical Trait',
            score: 82,
            raw_score: 18,
            max_score: 22,
            support_hits: 2,
            support_total: 2,
            band: 'strong',
            polarity: 'positive',
            domain: 'cognitive_style',
            family_representative: true,
            source_status: 'curated',
            source_lineage: 'classical',
            source_lineage_label: 'Classical source',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['mind'],
            keyword_layers: { morin: ['mind'], classical: ['study'] },
            citations: [{ citation_id: 'demetra:1', source_lineage: 'classical', source_label: 'Demetra George', excerpt: 'Study and judgment.' }],
          },
          {
            id: 'social_trait',
            name: 'Social Trait',
            score: 75,
            raw_score: 15,
            max_score: 20,
            support_hits: 2,
            support_total: 2,
            band: 'strong',
            polarity: 'positive',
            domain: 'social_function',
            family_representative: true,
            source_status: 'curated',
            source_lineage: 'carter',
            source_lineage_label: 'Carter-derived',
            provisional: false,
            summary_surface: 'general',
            summary_eligible: true,
            summary_priority: 0,
            keywords: ['friends'],
            keyword_layers: { morin: ['friends'] },
            citations: [],
          },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Constructive');
    fireEvent.click(screen.getByRole('button', { name: /Domains \(/ }));
    fireEvent.click(screen.getByLabelText('Select all'));
    fireEvent.click(screen.getByLabelText('social_function'));
    fireEvent.change(screen.getByLabelText('Band'), { target: { value: 'weak' } });

    expect(screen.getByText('No traits match the current filters.')).toBeTruthy();
    expect(screen.getByText(/Active filters: Band: weak.*Domains: 1\/2/)).toBeTruthy();

    fireEvent.click(screen.getAllByRole('button', { name: 'Reset filters' })[0]);
    await waitFor(() => {
      expect(screen.getByText('All Traits')).toBeTruthy();
      expect(screen.getAllByText('Classical Trait').length).toBeGreaterThan(0);
    });
  });

  it('prefers source-backed summary traits over editorial ones when fallback ordering is used', async () => {
    astroClockApiMock.getTraitProfile.mockResolvedValueOnce({
      success: true,
      data: {
        summary: {},
        special_degrees: [],
        top_traits: [],
        summary_traits: [
          { id: 'editorial_trait', name: 'Editorial Trait', score: 64, raw_score: 12.8, max_score: 20, support_hits: 1, support_total: 1, band: 'likely', polarity: 'positive', domain: 'cognitive_style', source_status: 'curated', source_lineage: 'editorial', source_lineage_label: 'Editorial', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['mind'] },
          { id: 'classical_trait', name: 'Classical Trait', score: 62, raw_score: 12.4, max_score: 20, support_hits: 1, support_total: 1, band: 'likely', polarity: 'positive', domain: 'cognitive_style', source_status: 'curated', source_lineage: 'classical', source_lineage_label: 'Classical source', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['mind'] },
        ],
        receptions: null,
        traits: [
          { id: 'editorial_trait', name: 'Editorial Trait', score: 64, raw_score: 12.8, max_score: 20, support_hits: 1, support_total: 1, band: 'likely', polarity: 'positive', domain: 'cognitive_style', family_representative: true, source_status: 'curated', source_lineage: 'editorial', source_lineage_label: 'Editorial', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['mind'] },
          { id: 'classical_trait', name: 'Classical Trait', score: 62, raw_score: 12.4, max_score: 20, support_hits: 1, support_total: 1, band: 'likely', polarity: 'positive', domain: 'cognitive_style', family_representative: true, source_status: 'curated', source_lineage: 'classical', source_lineage_label: 'Classical source', provisional: false, summary_surface: 'general', summary_eligible: true, summary_priority: 0, keywords: ['mind'] },
        ],
        house_influences: { houses: [] },
      },
    });

    render(
      <TraitProfileModal
        onClose={vi.fn()}
        specialDegrees={[]}
        mode="manual"
        manualIso="2026-03-22T06:32:00"
        manualLocation="Israel"
        timezone="Asia/Jerusalem"
        houseSystem="R"
        fixedStarHits={[]}
      />
    );

    await screen.findByText('Top Constructive');
    const topPositive = screen.getByText('Top Constructive').closest('div.border');
    const firstLabel = topPositive.querySelector('.font-medium.text-sm');
    expect(firstLabel.textContent).toContain('Classical Trait');
  });

  it('uses the ruler-route house instead of the leading H10 marker for profession suggestions', () => {
    const suggestions = buildProfessionSuggestions({
      house: 10,
      sign: 'Scorpio',
      basic_analysis: {
        route_line: 'H10 (career, honors, reputation): by governance Mars (ruler in H7); by aspect Moon opposition to cusp',
      },
      influences: [],
    }, {});

    const labels = suggestions.map((item) => item.label);
    expect(labels).toContain('legal practice');
    expect(labels).toContain('public advocacy');
    expect(labels).not.toContain('public administrator');
  });

  it('accepts textual ruler-route forms like "Ruler of 10 in 11"', () => {
    const suggestions = buildProfessionSuggestions({
      house: 10,
      sign: 'Taurus',
      basic_analysis: {
        route_line: 'Ruler of 10 in 11 — Friends/patrons elevate career and reputation.',
      },
      influences: [],
    }, {});

    const labels = suggestions.map((item) => item.label);
    expect(labels).toContain('political organizer');
    expect(labels).toContain('association director');
  });

  it('accepts backend ruler-route prose like "They proceed via its ruler Mars in House 7"', () => {
    const suggestions = buildProfessionSuggestions({
      house: 10,
      sign: 'Scorpio',
      basic_analysis: {
        ruler_map: {
          route: 'They proceed via its ruler Mars in House 7 — Career via partnership; public marriage.',
        },
      },
      influences: [],
    }, {});

    const labels = suggestions.map((item) => item.label);
    expect(labels).toContain('legal practice');
    expect(labels).toContain('public advocacy');
  });

  it('keeps a ruler-route suggestion in the top profession list when generic planet roles would crowd it out', () => {
    const suggestions = buildProfessionSuggestions({
      house: 10,
      sign: 'Scorpio',
      basic_analysis: {
        determinators_panel: {
          governance: [{ planet: 'Mars', type: 'rulership', rank: 'dominant', value: 40 }],
        },
        ruler_map: {
          route: 'They proceed via its ruler Mars in House 7 — Career via partnership; public marriage.',
          conditions: ['Angular ruler manifests readily.'],
        },
      },
      influences: [],
    }, {});

    const labels = suggestions.map((item) => item.label);
    expect(suggestions.length).toBeLessThanOrEqual(8);
    expect(labels).toContain('legal practice');
  });

  it('does not surface judiciary as a generic Sun/Jupiter vocation without legal context', () => {
    const suggestions = buildProfessionSuggestions({
      house: 10,
      sign: 'Aquarius',
      basic_analysis: {
        determinators_panel: {
          presence: [{ planet: 'Jupiter', rank: 'dominant', value: 50 }],
        },
        ruler_map: {
          route: 'They proceed via its ruler Saturn in House 11 — Friends/patrons elevate career and reputation.',
        },
      },
      influences: [{ planet: 'Jupiter', type: 'occupation', value: 50 }],
    }, {});

    const labels = suggestions.map((item) => item.label);
    expect(labels).toContain('professor');
    expect(labels).not.toContain('judge/magistrate');
    expect(labels).not.toContain('judiciary');
  });

  it('still permits judiciary-family labels when the chart has real legal context', () => {
    const suggestions = buildProfessionSuggestions({
      house: 10,
      sign: 'Libra',
      basic_analysis: {
        determinators_panel: {
          presence: [{ planet: 'Jupiter', rank: 'dominant', value: 50 }],
        },
        ruler_map: {
          route: 'They proceed via its ruler Venus in House 7 — Career via partnership and public litigation.',
        },
      },
      influences: [{ planet: 'Jupiter', type: 'occupation', value: 50 }],
    }, {});

    const labels = suggestions.map((item) => item.label);
    expect(labels.some((label) => ['judge/magistrate', 'law', 'legal practice'].includes(label))).toBe(true);
  });
});
