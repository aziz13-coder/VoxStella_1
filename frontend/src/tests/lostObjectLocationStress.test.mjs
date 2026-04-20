import { describe, expect, test } from 'vitest';

import { buildChartPayload } from '../utils/buildChartPayload.js';
import { normalizeHoraryApiResult } from '../utils/normalizeHoraryApiResult.mjs';
import {
  hasLostObjectLocationProjection,
  isMissingPetLocationChart,
  shouldShowLostObjectLocationTab,
} from '../features/horary/lostObjectLocation.mjs';

const projection = {
  applies: true,
  summary: 'In a workplace; near the doorway; on the floor.',
  primary_places: [{ label: 'In a workplace, home office, formal room, or parent\'s area' }],
  environment_traits: [{ label: 'Close to the doorway, threshold, or entrance of that room' }],
  evidence: [{ factor: 'house', clue: 'In a workplace, home office, formal room, or parent\'s area' }],
};

describe('lost-object location frontend stress matrix', () => {
  test.each([
    {
      label: 'standard lost object chart with projection',
      chart: {
        question_analysis: { question_type: 'LOST_OBJECT' },
        lost_object_location: projection,
      },
      expected: true,
    },
    {
      label: 'bridged passport chart with projection',
      chart: {
        question_analysis: { question_type: 'GENERAL' },
        traditional_factors: { perfection_type: 'lost_object_discovery_balance' },
        lost_object_location: projection,
      },
      expected: true,
    },
    {
      label: 'missing pet chart with projection',
      chart: {
        question_analysis: {
          question_type: 'PET',
          significators: { pet_family: 'missing' },
        },
        traditional_factors: { perfection_type: 'pet_missing_balance' },
        lost_object_location: projection,
      },
      expected: true,
    },
    {
      label: 'lost object chart without projection',
      chart: {
        question_analysis: { question_type: 'LOST_OBJECT' },
        lost_object_location: { applies: false },
      },
      expected: false,
    },
    {
      label: 'general chart without projection',
      chart: {
        question_analysis: { question_type: 'GENERAL' },
      },
      expected: false,
    },
  ])('tab gate handles $label', ({ chart, expected }) => {
    expect(hasLostObjectLocationProjection(chart)).toBe(expected);
  });

  test.each([
    {
      label: 'legacy lost object chart without projection still shows the tab',
      chart: {
        question_analysis: {
          question_type: 'Category.LOST_OBJECT',
          significators: { lost_object_family: 'discovery' },
        },
        lost_object_location: { applies: false },
      },
      expected: true,
    },
    {
      label: 'bridged lost passport chart without projection still shows the tab',
      chart: {
        question_analysis: {
          question_type: 'GENERAL',
          significators: { passport_family: 'passport_lost_document' },
        },
      },
      expected: true,
    },
    {
      label: 'non lost-object chart without projection still hides the tab',
      chart: {
        question_analysis: { question_type: 'GENERAL', significators: {} },
      },
      expected: false,
    },
  ])('tab visibility helper handles $label', ({ chart, expected }) => {
    expect(shouldShowLostObjectLocationTab(chart)).toBe(expected);
  });

  test('legacy missing-pet charts still show the location tab before rerun repopulates the projection', () => {
    const chart = {
      question_analysis: {
        question_type: 'Category.PET',
        pet_analysis: { family: 'missing' },
        significators: { pet_family: 'missing' },
      },
      traditional_factors: { perfection_type: 'pet_missing_balance' },
      lost_object_location: { applies: false },
    };

    expect(isMissingPetLocationChart(chart)).toBe(true);
    expect(hasLostObjectLocationProjection(chart)).toBe(false);
    expect(shouldShowLostObjectLocationTab(chart)).toBe(true);
  });

  test('normalization and export preserve bridged passport location payloads', () => {
    const normalized = normalizeHoraryApiResult({
      judgment: 'YES',
      question_analysis: { question_type: 'GENERAL' },
      lost_object_location: projection,
      traditional_factors: { perfection_type: 'lost_object_discovery_balance' },
    });

    const payload = buildChartPayload(
      {
        id: 1,
        question: "Where's my passport?",
        tags: ['general'],
        chart_data: { timezone_info: { timezone: 'Europe/London', utc_time: '2003-01-24T10:46:00.000Z' } },
        traditional_factors: normalized.traditional_factors,
        lost_object_location: normalized.lost_object_location,
        reasoning: [],
        judgment: normalized.judgment,
        confidence: 72,
      },
      true,
      false,
    );

    expect(normalized.lost_object_location).toEqual(projection);
    expect(payload.lost_object_location).toEqual(projection);
  });

  test('normalization and export preserve missing-pet location payloads across rerun-style updates', () => {
    const normalized = normalizeHoraryApiResult(
      {
        judgment: 'YES',
        question_analysis: {
          question_type: 'PET',
          pet_analysis: { family: 'missing' },
          significators: { pet_family: 'missing' },
        },
        lost_object_location: projection,
        traditional_factors: { perfection_type: 'pet_missing_balance' },
      },
      {
        existingChart: {
          id: 77,
          judgment: 'NO',
          outcome: 'negative',
          confidence: 84,
          tags: ['pet'],
        },
      },
    );

    const payload = buildChartPayload(
      {
        id: normalized.id,
        question: 'Will my dog come home?',
        tags: normalized.tags,
        chart_data: { timezone_info: { timezone: 'America/New_York', utc_time: '2025-01-07T04:19:00.000Z' } },
        traditional_factors: normalized.traditional_factors,
        question_analysis: normalized.question_analysis,
        lost_object_location: normalized.lost_object_location,
        reasoning: [],
        judgment: normalized.judgment,
        confidence: normalized.confidence,
      },
      true,
      false,
    );

    expect(normalized.id).toBe(77);
    expect(normalized.tags).toEqual(['pet']);
    expect(normalized.outcome).toBe('positive');
    expect(normalized.lost_object_location).toEqual(projection);
    expect(payload.lost_object_location).toEqual(projection);
  });
});
