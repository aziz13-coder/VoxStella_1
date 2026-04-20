import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import LostObjectLocationPanel from '../features/horary/LostObjectLocationPanel.jsx';
import {
  formatHouseLabel,
  hasLostObjectLocationProjection,
  isMissingPetLocationChart,
  shouldShowLostObjectLocationTab,
} from '../features/horary/lostObjectLocation.mjs';

const chart = {
  question_analysis: { question_type: 'LOST_OBJECT' },
  lost_object_location: {
    applies: true,
    object_significator: 'Mercury',
    effective_house: 7,
    object_sign: 'Pisces',
    sign_element: 'Water',
    sign_modality: 'Mutable',
    summary: 'With a partner or among another person\'s belongings; near water; inside a bag.',
    confidence: 78,
    confidence_label: 'moderate',
    primary_places: [
      {
        label: 'With a partner, spouse, or among another person\'s belongings',
        reason: '7th house placement of Mercury',
      },
    ],
    secondary_places: [
      {
        label: 'In a workplace, home office, formal room, or parent\'s area',
        reason: 'The dispositor gives a second clue',
      },
    ],
    environment_traits: [
      {
        label: 'Near water, bathrooms, kitchens, sinks, damp areas, or washing items',
        reason: 'Water signs point to damp places',
      },
      {
        label: 'Inside something movable: a bag, box, drawer, pocket, or container',
        reason: 'Mutable signs often place the object inside something',
      },
    ],
    directional_cues: [{ label: 'North by West', reason: 'Pisces gives the traditional bearing North by West' }],
    evidence: [
      {
        factor: 'house',
        clue: 'With a partner, spouse, or among another person\'s belongings',
        rule: '7th house placement of Mercury',
      },
    ],
  },
};

const passportChart = {
  question_analysis: { question_type: 'GENERAL' },
  traditional_factors: { perfection_type: 'lost_object_discovery_balance' },
  lost_object_location: {
    applies: true,
    object_significator: 'Mercury',
    effective_house: 10,
    object_sign: 'Capricorn',
    sign_element: 'Earth',
    sign_modality: 'Cardinal',
    summary: 'In a workplace, home office, formal room, or parent\'s area; close to the doorway; on or near the floor.',
    confidence: 82,
    confidence_label: 'high',
    primary_places: [
      {
        label: 'In a workplace, home office, formal room, or parent\'s area',
        reason: '10th house placement of Mercury',
      },
    ],
    secondary_places: [
      {
        label: 'Check desks, papers, folders, travel items, or an office-style surface',
        reason: 'Documents keep a Mercurial tone even when the house gives the main location',
      },
    ],
    environment_traits: [
      {
        label: 'Close to the doorway, threshold, or entrance of that room',
        reason: 'Mercury lies close to the next cusp in the same sign',
      },
      {
        label: 'On or near the floor, in storage, a pantry, cellar, or garden-side place',
        reason: 'Earth signs point to low places, floors, and practical storage',
      },
    ],
    directional_cues: [{ label: 'South', reason: 'Capricorn gives the traditional bearing South' }],
    evidence: [
      {
        factor: 'house',
        clue: 'In a workplace, home office, formal room, or parent\'s area',
        rule: '10th house placement of Mercury',
      },
      {
        factor: 'element',
        clue: 'On or near the floor, in storage, a pantry, cellar, or garden-side place',
        rule: 'Earth signs point to low places, floors, and practical storage',
      },
    ],
  },
};

const missingPetChart = {
  question_analysis: {
    question_type: 'PET',
    pet_analysis: { family: 'missing' },
    significators: { pet_family: 'missing' },
  },
  traditional_factors: { perfection_type: 'pet_missing_balance' },
  lost_object_location: {
    applies: true,
    object_significator: 'Jupiter',
    effective_house: 4,
    object_sign: 'Gemini',
    sign_element: 'Air',
    sign_modality: 'Mutable',
    summary: 'Near home ground and openings; search toward West by South.',
    confidence: 84,
    confidence_label: 'high',
    primary_places: [
      {
        label: 'Near home ground, the yard, garage, shed, garden, or low places',
        reason: '4th house placement of the pet significator',
      },
    ],
    secondary_places: [
      {
        label: 'Near roads, openings, stairs, breezy places, or raised sight-lines',
        reason: 'Gemini refines the search space',
      },
    ],
    environment_traits: [
      {
        label: 'Between places, on the move, along a route, or near bags/containers/openings',
        reason: 'Mutable signs often show movement or transitional spaces',
      },
    ],
    directional_cues: [{ label: 'West by South', reason: 'Gemini gives the traditional bearing West by South' }],
    evidence: [
      {
        factor: 'house',
        clue: 'Near home ground, the yard, garage, shed, garden, or low places',
        rule: '4th house placement of the pet significator',
      },
    ],
  },
};

describe('LostObjectLocationPanel', () => {
  test('renders projected place sections for lost-object charts', () => {
    render(<LostObjectLocationPanel chart={chart} darkMode={false} />);

    const summaryCard = screen.getByTestId('lost-object-location-summary-card');
    const sectionTabs = screen.getByTestId('lost-object-location-section-tabs');

    expect(screen.getByRole('button', { name: 'Primary Places' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Further Clues' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Direction' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Evidence' })).toBeInTheDocument();
    expect(summaryCard.contains(sectionTabs)).toBe(false);

    expect(screen.getByRole('heading', { name: 'Primary Places' })).toBeInTheDocument();
    expect(screen.getAllByText(/among another person's belongings/i).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: 'Further Clues' }));
    expect(screen.getByText(/inside something movable/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Direction' }));
    expect(screen.getByText('North by West')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(screen.getByText('house')).toBeInTheDocument();
  });

  test('renders real-answer style passport clues in the location tab', () => {
    render(<LostObjectLocationPanel chart={passportChart} darkMode={false} />);

    expect(screen.getAllByText(/home office/i).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: 'Further Clues' }));
    expect(screen.getAllByText(/doorway|threshold|entrance/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/on or near the floor/i).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: 'Direction' }));
    expect(screen.getByText('South')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(screen.getAllByText(/home office/i).length).toBeGreaterThan(0);
    expect(screen.getByText('element')).toBeInTheDocument();
  });

  test('gating helper only enables the tab when projection data is present', () => {
    expect(hasLostObjectLocationProjection(chart)).toBe(true);
    expect(shouldShowLostObjectLocationTab(chart)).toBe(true);
    expect(isMissingPetLocationChart(missingPetChart)).toBe(true);
    expect(shouldShowLostObjectLocationTab(missingPetChart)).toBe(true);
    expect(
      hasLostObjectLocationProjection({
        question_analysis: { question_type: 'LOST_OBJECT' },
        lost_object_location: { applies: false },
      }),
    ).toBe(false);
    expect(
      shouldShowLostObjectLocationTab({
        question_analysis: { question_type: 'LOST_OBJECT' },
        lost_object_location: { applies: false },
      }),
    ).toBe(true);
    expect(
      hasLostObjectLocationProjection({
        question_analysis: { question_type: 'GENERAL' },
        lost_object_location: { applies: true },
      }),
    ).toBe(true);
    expect(
      shouldShowLostObjectLocationTab({
        question_analysis: { question_type: 'GENERAL' },
        lost_object_location: { applies: true },
      }),
    ).toBe(true);
    expect(formatHouseLabel(7)).toBe('7th house');
  });

  test('shows rerun guidance for saved lost-object charts without structured location clues', () => {
    render(
      <LostObjectLocationPanel
        chart={{
          question_analysis: {
            question_type: 'Category.LOST_OBJECT',
            significators: { lost_object_family: 'discovery' },
          },
          lost_object_location: { applies: false },
        }}
        darkMode={false}
      />,
    );

    expect(
      screen.getByText(/does not yet include the newer structured location projection/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/re-run the chart with the current engine build/i),
    ).toBeInTheDocument();
  });

  test('shows rerun guidance for saved missing-pet charts without structured location clues', () => {
    render(
      <LostObjectLocationPanel
        chart={{
          question_analysis: {
            question_type: 'PET',
            pet_analysis: { family: 'missing' },
            significators: { pet_family: 'missing' },
          },
          traditional_factors: { perfection_type: 'pet_missing_balance' },
          lost_object_location: { applies: false },
        }}
        darkMode={false}
      />,
    );

    expect(
      screen.getByText(/this chart is a missing-pet case/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/re-run the chart with the current engine build/i),
    ).toBeInTheDocument();
  });
});
