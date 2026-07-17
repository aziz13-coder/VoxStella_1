import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ChineseAstrologyPage from '../features/astroclock/ChineseAstrologyPage.jsx';
import { AstroClockAPI } from '../features/astroclock/api.mjs';

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: {
    getChineseAstrologyBazi: vi.fn(),
    getChineseAstrologyCompatibility: vi.fn(),
    getChineseAstrologyIChingOracle: vi.fn(),
    listSnaps: vi.fn(),
  },
}));

const snapA = {
  id: 'snap-a',
  label: 'Primary Example With A Long Saved Snap Label',
  effective_datetime: '2026-02-04T00:02:00Z',
  location: 'Greenwich, UK',
  timezone: 'UTC',
  longitude: 0,
};

const snapB = {
  id: 'snap-b',
  label: 'Relationship Example',
  effective_datetime: '2026-03-05T13:00:00Z',
  location: 'London, UK',
  timezone: 'UTC',
  longitude: 0,
};

function pillar(stem, branch, element = 'Wood', overrides = {}) {
  return {
    stem,
    stem_element: element,
    stem_polarity: 'yang',
    branch,
    branch_element: overrides.branch_element || element,
    branch_polarity: 'yang',
    animal: overrides.animal || branch,
    hidden_stems: overrides.hidden_stems || [],
    ten_god: overrides.ten_god || 'Peer',
    ...overrides,
  };
}

function makeProfile(overrides = {}) {
  return {
    source_snap_id: 'snap-a',
    snap_label: 'Primary Example With A Long Saved Snap Label',
    source_confidence: [
      { key: 'computed_rule', label: 'Computed rule' },
      { key: 'needs_validation', label: 'Needs validation' },
    ],
    birth: {
      local_datetime: '2026-02-04T00:02:00+00:00',
      timezone: 'UTC',
      calculation_options: {
        day_boundary_rule: 'civil_midnight',
        hour_pillar_variant: 'standard_zi_hour',
        luck_direction_rule: 'year_stem_polarity',
      },
      true_solar_time: { requested: false },
    },
    pillars: {
      hour: pillar('Jia', 'Zi', 'Wood'),
      day: pillar('Ji', 'You', 'Earth'),
      month: pillar('Geng', 'Yin', 'Metal'),
      year: pillar('Bing', 'Wu', 'Fire'),
    },
    day_master: { stem: 'Ji', element: 'Earth', polarity: 'yin' },
    analysis: {
      strength: 'balanced',
      strength_evidence: ['Season and roots are mixed.'],
      strength_model: {
        method: 'season_root_formation_v2',
        confidence: 'medium',
        weighted_score: 0.2,
        season: { season: 'Autumn', state: 'very weak' },
        root: { score: 1.05, root_grade: 'minor_root' },
        formation: { score: -0.5 },
        root_grade_evidence: {
          method: 'root_grade_evidence_v1',
          de_ling: { status: 'lost', evidence: 'Autumn season weakens the Day Master.' },
          de_di: { status: 'resource_only', root_grade: 'minor_root', evidence: 'Resource support appears without a same-element root.' },
          de_zhu: { status: 'neutral', evidence: 'Visible pillars are mixed.' },
          resource_substitute_limit: {
            active: true,
            note: 'Resource does not fully replace a real root.',
          },
        },
      },
    },
    element_balance: {
      counts: { Wood: 1, Fire: 1, Earth: 1, Metal: 1, Water: 0 },
      dominant: 'Wood',
      missing: ['Water'],
    },
    useful_elements: {
      status: 'provisional',
      confidence: 'seed',
      day_master_strength: 'balanced',
      favorable: [],
      unfavorable: [],
      candidates_to_watch: [],
      element_integrity: [],
      climate_adjustment: { recommendations: [] },
      damage_assessment: [],
      damage_summary: {},
      useful_god: {
        final_status: 'withheld',
        candidate_status: 'withheld',
        decision_path: 'yong_shen.balanced_withheld',
        confidence: 'low',
        reason: 'The app does not name a final Yong Shen for balanced charts.',
        blocking_reasons: ['strength_not_decisive', 'final_fixture_not_curated'],
        evidence: {
          strength: {
            label: 'balanced',
            support_score: 4,
            pressure_score: 4,
            model_confidence: 'medium',
          },
          climate: {
            status: 'source_based_preview',
            override_status: 'watch',
            season: 'Winter',
          },
          presence: {
            availability: 'missing',
            pressure: 'clear',
          },
          damage: {
            status: 'absent',
            reason: 'The primary favorable element is not available in natal placements.',
          },
          special_structure: {
            status: 'screened_not_classified',
            structure_status: 'none',
            flags: [],
          },
          timing: {
            status: 'not_enabled',
            items: [],
          },
          fixture_gate: {
            family: 'balanced_withheld',
            released: false,
            positive_fixture_count: 0,
            negative_fixture_count: 1,
            fixture_ids: ['yong_shen.strong_balancing.negative.balanced_chart'],
            blockers: ['release_not_enabled'],
          },
        },
        source_ids: ['local.destiny_code_favorable_elements'],
        fixture_ids: [],
        source_evidence: [
          {
            source_id: 'local.destiny_code_favorable_elements',
            rule_id: 'yong_shen.balanced_withheld',
            claim: 'Final Yong Shen is gated by source-backed fixtures.',
            fixture_ids: ['yong_shen.strong_balancing.negative.balanced_chart'],
          },
        ],
      },
      special_structure_screen: { flags: [] },
      notes: [],
    },
    interpretation: {
      summary: 'Ji Earth Day Master, currently reading as balanced strength.',
      sections: [{ title: 'Reading Focus', items: ['Day Master evidence stays central.'] }],
    },
    ten_gods: { visible: [], hidden: [], factor_profile: { factors: [] } },
    palace_context: { palaces: [], focus: {} },
    life_areas: { status: 'source_gated_context', areas: [], context_requirements: [], limits: [] },
    relationships: { events: [], summary: { total: 0 }, source_confidence: [] },
    auxiliary_stars: { peach_blossom: { status: 'unavailable' }, notes: [] },
    timing: {
      luck_pillars_enabled: false,
      annual_pillar: { stem: 'Bing', branch: 'Wu', bazi_year: 2026 },
      luck_pillars: [],
      active_luck_pillar: null,
      useful_element_interaction: {
        status: 'not_enabled',
        summary: 'Luck Pillar interaction requires an enabled decade sequence.',
        items: [],
      },
      debug: { method: 'luck_pillars_require_calculation_sex' },
    },
    luck_pillars: [],
    missing_inputs: [{ field: 'calculation_sex', message: 'Calculation sex is required for Luck Pillars.' }],
    curation: {
      needs_validation: ['strength.season_root_formation'],
      validation: {
        status: 'validation_fixture_ledger_seeded',
        phase_count: 6,
        fixture_count: 97,
        p0_fixture_count: 28,
        needs_external_anchor: [],
        advanced_rule_families: [
          {
            family: 'strong_balancing',
            released: true,
            positive_fixture_count: 3,
            negative_fixture_count: 3,
            blockers: [],
          },
          {
            family: 'climate_override',
            released: false,
            positive_fixture_count: 3,
            negative_fixture_count: 3,
            blockers: ['release_not_enabled'],
          },
          {
            family: 'special_structure_withheld',
            released: false,
            positive_fixture_count: 0,
            negative_fixture_count: 1,
            blockers: ['release_not_enabled'],
          },
          {
            family: 'dominant_element',
            released: false,
            positive_fixture_count: 3,
            negative_fixture_count: 3,
            blockers: ['release_not_enabled'],
          },
          {
            family: 'damaged_alternate',
            released: false,
            positive_fixture_count: 3,
            negative_fixture_count: 3,
            blockers: ['release_not_enabled'],
          },
          {
            family: 'timing_assisted',
            released: false,
            positive_fixture_count: 3,
            negative_fixture_count: 3,
            blockers: ['release_not_enabled'],
          },
        ],
        phases: [
          {
            id: 'V1',
            title: 'Calendar And Pillar Correctness',
            priority: 'P0',
            status: 'fixture_ledger_seeded',
            fixture_count: 17,
            areas: ['solar_terms', 'day_cycle', 'hour_pillar'],
          },
        ],
      },
    },
    debug: {
      snap_source: 'saved_snap',
      solar_term_source: 'swiss_ephemeris',
      calculation_options: {
        day_boundary_rule: 'civil_midnight',
        hour_pillar_variant: 'standard_zi_hour',
        luck_direction_rule: 'year_stem_polarity',
      },
      warnings: [],
    },
    ...overrides,
  };
}

function makeRhythm() {
  const layer = (name, label, stem, branch, tone = 'mixed') => ({
    layer: name,
    label,
    scope: name === 'da_yun' ? 'luck' : name,
    pillar: {
      stem,
      branch,
      animal: branch,
      stem_element: 'Fire',
      branch_element: 'Earth',
      ten_god: 'Direct Resource',
      five_factor: 'Resource',
    },
    ten_god: { stem: 'Direct Resource', factor: 'Resource' },
    useful_element_effects: [
      {
        placement: 'stem',
        symbol: stem,
        source_element: 'Fire',
        target_role: 'favorable',
        target_element: 'Earth',
        effect: 'supports',
        status: 'supports_favorable',
      },
    ],
    relationship_events: [],
    relationship_summary: { total: 0, supportive: 0, challenging: 0, mixed: 0 },
    interpretive_effects: name === 'flowing_day'
      ? [
          {
            kind: 'movement',
            source: 'relationship_contact',
            event_type: 'branch_clash',
            label: 'Si-Hai clash',
            summary: 'Si-Hai clash marks movement during Flowing Day.',
          },
        ]
      : [],
    growth_stage: {
      status: 'source_backed_preview',
      stage: 'di_wang',
      label: 'Di Wang',
      meaning: 'imperial peak',
      group: 'peak',
      page_ref: { source_id: 'local.four_pillars_growth_stages', pages: [63] },
    },
    calculation_basis: {
      method: 'computed_sexagenary',
      boundary_used: {},
      source_page_refs: [],
    },
    evidence_role: 'contextual_timing_only',
    source_strength: name === 'da_yun' || name === 'liu_nian' ? 'local_worked_example' : 'computed_no_worked_example',
    release_gate: name === 'flowing_month' || name === 'flowing_day' || name === 'flowing_hour'
      ? 'preview_only_until_worked_examples_curated'
      : 'timing_assisted_finalization_blocked',
    score: tone === 'supportive' ? 4 : 1,
    tone,
  });
  return {
    status: 'source_based_preview',
    method: 'bazi_timing_rhythm_v1',
    scope: 'bazi_timing_not_branded_fortune_cycle',
    reference_datetime_utc: '2026-05-11T00:00:00+00:00',
    summary: 'Current timing is supportive: the active layers add usable support signals.',
    layers: [
      layer('da_yun', 'Current 10-Year Luck', 'Geng', 'Chen', 'supportive'),
      layer('liu_nian', 'Current BaZi Year', 'Bing', 'Wu', 'mixed'),
      layer('flowing_month', 'Flowing Month', 'Gui', 'Si', 'mixed'),
      layer('flowing_day', 'Flowing Day', 'Yi', 'Hai', 'mixed'),
      layer('flowing_hour', 'Flowing Hour', 'Bing', 'Zi', 'mixed'),
    ],
    event_activation: {
      status: 'active',
      summary: '5 timing layers activating chart evidence now.',
      primary_triggers: [
        {
          layer: 'flowing_month',
          label: 'Flowing Month',
          activation_role: 'event_window',
          activation_role_label: 'Timing Window',
          activation_score: 9,
          main_position_linked: true,
          status: 'event_trigger',
          status_label: 'Event Trigger',
          counts: {
            main_position_contacts: 3,
            rescue_arrival_signals: 1,
            pressure_movement_signals: 3,
          },
          summary: 'flowing_month event trigger: 3 Day/spouse-palace contact(s), 1 rescue/arrival signal(s), 3 pressure/movement signal(s).',
        },
        {
          layer: 'flowing_day',
          label: 'Flowing Day',
          activation_role: 'day_trigger',
          activation_role_label: 'Day Trigger',
          activation_score: 7,
          main_position_linked: true,
          status: 'event_trigger',
          status_label: 'Event Trigger',
          counts: {
            main_position_contacts: 2,
            rescue_arrival_signals: 1,
            pressure_movement_signals: 2,
          },
          summary: 'flowing_day event trigger: 2 Day/spouse-palace contact(s), 1 rescue/arrival signal(s), 2 pressure/movement signal(s).',
        },
      ],
    },
    source_evidence: [
      {
        source_id: 'anchor.timing.luck_pillars',
        rule_id: 'timing_rhythm.da_yun_liu_nian_flowing_layers',
        claim: 'The rhythm is built from Da Yun, annual, month, day, and hour pillars.',
        fixture_ids: ['timing_rhythm.current_layers_reference'],
      },
    ],
    source_confidence: [{ key: 'local_source', label: 'Local source' }, { key: 'computed_rule', label: 'Computed rule' }],
    calibration: {
      status: 'calibration_seeded_preview',
      fixture_ids: [
        'timing_rhythm.current_layers_reference',
        'timing_rhythm.growth_stage_day_master_branch',
        'timing_rhythm.flowing_month_contact_reference',
        'timing_rhythm.flowing_day_hour_contact_reference',
      ],
      layer_count: 5,
      flow_layer_count: 3,
      contact_layer_count: 2,
      release_gate: 'timing_assisted_finalization_blocked',
    },
    limits: [],
  };
}

function makeProfileWithLuck(overrides = {}) {
  const activeLuck = {
    sequence: 1,
    stem: 'Xin',
    branch: 'Mao',
    stem_element: 'Metal',
    branch_element: 'Wood',
    animal: 'Rabbit',
    ten_god: 'Output',
    five_factor: 'Output',
    age_label: '9y 10m - 19y 10m',
    calendar_start_year: 2035,
    calendar_end_year: 2045,
    active: true,
  };
  return makeProfile({
    missing_inputs: [],
    timing: {
      luck_pillars_enabled: true,
      direction: 'forward',
      direction_rule: 'yang-year male / yin-year female forward; opposite combinations reverse',
      direction_rule_key: 'year_stem_polarity',
      start_age: 9.86,
      start_age_label: '9y 10m',
      start_date: '2035-12-15',
      annual_pillar: { stem: 'Bing', branch: 'Wu', bazi_year: 2026 },
      active_luck_pillar: activeLuck,
      rhythm: makeRhythm(),
      useful_element_interaction: {
        status: 'quiet',
        summary: 'No active Luck Pillar or annual layer directly supplies, supports, or pressures the favorable candidates.',
        items: [],
      },
      luck_pillars: [activeLuck],
      debug: {
        method: 'three_days_per_year_from_adjacent_jie_solar_term',
        solar_term: { key: 'jing_zhe', name: 'Jing Zhe' },
        distance_days: 29.58,
        direction_rule_key: 'year_stem_polarity',
      },
    },
    luck_pillars: [activeLuck],
    ...overrides,
  });
}

function relationshipEvent(scope, label) {
  return {
    id: `${scope}-${label}`,
    type: 'branch_clash',
    label,
    scope,
    scope_label: label,
    intensity: 'indirect',
    symbols: ['Zi', 'Wu'],
    affected_palaces: ['Day', label],
    affected_domains: ['Self / partner palace', label],
  };
}

function makeOracle() {
  const lines = [
    { position: 1, value: 6, label: 'old yin', visual: 'broken', resulting_label: 'young yang', resulting_visual: 'solid', moving: true, changes_to: 7, position_focus: 'foundation' },
    { position: 2, value: 7, label: 'young yang', visual: 'solid', resulting_label: 'young yang', resulting_visual: 'solid', moving: false, changes_to: 7, position_focus: 'inner alignment' },
    { position: 3, value: 8, label: 'young yin', visual: 'broken', resulting_label: 'young yin', resulting_visual: 'broken', moving: false, changes_to: 8, position_focus: 'threshold' },
    { position: 4, value: 9, label: 'old yang', visual: 'solid', resulting_label: 'young yin', resulting_visual: 'broken', moving: true, changes_to: 8, position_focus: 'outer field' },
    { position: 5, value: 7, label: 'young yang', visual: 'solid', resulting_label: 'young yang', resulting_visual: 'solid', moving: false, changes_to: 7, position_focus: 'governing center' },
    { position: 6, value: 8, label: 'young yin', visual: 'broken', resulting_label: 'young yin', resulting_visual: 'broken', moving: false, changes_to: 8, position_focus: 'completion' },
  ];
  return {
    method: 'iching_oracle_v1',
    question: 'How should we proceed?',
    casting_method: 'manual_lines',
    line_order: 'bottom_to_top',
    coin_value_scheme: 'heads_2_tails_3',
    cast_source: 'provided_manual_lines',
    random_model: 'none',
    lines,
    changing_lines: [1, 4],
    moving_line_focus: [
      { position: 1, transition: 'opens from yin into yang', focus: 'foundation' },
      { position: 4, transition: 'settles from yang into yin', focus: 'outer field' },
    ],
    primary: {
      number: 60,
      pinyin: 'Jie',
      title: 'Limitation',
      label: '60. Limitation',
      keywords: ['bounds', 'measure'],
      theme: 'Good limits make action sustainable.',
      counsel: 'Set limits that serve life.',
      upper_trigram: { name: 'Dui', image: 'Lake' },
      lower_trigram: { name: 'Kan', image: 'Water' },
    },
    relating: {
      number: 47,
      pinyin: 'Kun',
      title: 'Oppression',
      label: '47. Oppression',
      keywords: ['constraint'],
      theme: 'Outer resources are constrained.',
      counsel: 'Conserve strength.',
      upper_trigram: { name: 'Kan', image: 'Water' },
      lower_trigram: { name: 'Dui', image: 'Lake' },
    },
    nuclear: {
      number: 50,
      pinyin: 'Ding',
      title: 'The Cauldron',
      label: '50. The Cauldron',
      keywords: ['transformation'],
      theme: 'Raw material can be transformed.',
      counsel: 'Tend the vessel.',
      upper_trigram: { name: 'Xun', image: 'Wind' },
      lower_trigram: { name: 'Li', image: 'Fire' },
      line_visuals_bottom_to_top: ['solid', 'broken', 'solid', 'broken', 'solid', 'solid'],
      derivation: { lower_nuclear_lines: [2, 3, 4], upper_nuclear_lines: [3, 4, 5] },
    },
    reading: {
      summary: 'Good limits make action sustainable. The changing lines move the matter toward 47. Oppression.',
      primary_counsel: 'Set limits that serve life.',
      policy: {
        id: 'zhu_xi_seven_rule_line_policy',
        label: 'Zhu Xi seven-rule line focus',
        focus: 'two_moving_lines_upper_primary',
        selected_lines: [1, 4],
        primary_line: 4,
        summary: 'Two lines change, so both primary moving lines are read, with line 4 carrying the stronger focus.',
      },
    },
    source_confidence: [{ key: 'source_backed_structural_oracle', label: 'Structure source-backed' }],
    source_evidence: [
      { source_id: 'local.iching_huang', claim: 'Local corpus anchor for I Ching casting terminology.' },
      { source_id: 'public.iching_divination_method', claim: 'Line numbers and changing lines are source anchored.' },
    ],
  };
}

describe('ChineseAstrologyPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    AstroClockAPI.listSnaps.mockResolvedValue({ success: true, items: [snapA, snapB] });
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({ success: true, data: makeProfile() });
    AstroClockAPI.getChineseAstrologyCompatibility.mockResolvedValue({
      success: true,
      data: { compatibility: null },
    });
    AstroClockAPI.getChineseAstrologyIChingOracle.mockResolvedValue({
      success: true,
      data: { oracle: makeOracle() },
    });
  });

  it('renders primary calculation sex as a global control instead of a Timing-only control', async () => {
    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    expect(screen.getByText('BaZi Profile / chart memo')).toBeInTheDocument();
    const globalGroup = screen.getByText('primary calculation sex').closest('div');
    expect(within(globalGroup).getByRole('button', { name: 'primary calculation sex: Not Set' })).toBeInTheDocument();

    fireEvent.click(within(globalGroup).getByRole('button', { name: 'primary calculation sex: Not Set' }));
    expect(within(globalGroup).getByRole('option', { name: 'Not Set' })).toBeInTheDocument();
    expect(within(globalGroup).getByRole('option', { name: 'Female' })).toBeInTheDocument();
    expect(within(globalGroup).getByRole('option', { name: 'Male' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Life Timing' }));
    expect(await screen.findByRole('heading', { name: 'Life Timing' })).toBeInTheDocument();
    expect(screen.queryByText('Luck Direction Basis')).not.toBeInTheDocument();
    expect(screen.getByText(/Set Primary Calculation Sex in the controls/)).toBeInTheDocument();
  });

  it('renders Four Pillars with Chinese characters and readable hidden stems', async () => {
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({
      success: true,
      data: makeProfile({
        pillars: {
          hour: pillar('Jia', 'Zi', 'Wood', {
            animal: 'Rat',
            branch_element: 'Water',
            hidden_stems: [{ key: 'Gui', element: 'Water', god: 'Direct Wealth', rank: 1 }],
            ten_god: 'Direct Officer',
          }),
          day: pillar('Ji', 'You', 'Earth', {
            animal: 'Rooster',
            branch_element: 'Metal',
            hidden_stems: [{ key: 'Xin', element: 'Metal', god: 'Eating God', rank: 1 }],
            ten_god: 'Day Master',
          }),
          month: pillar('Geng', 'Yin', 'Metal', {
            animal: 'Tiger',
            branch_element: 'Wood',
            hidden_stems: [{ key: 'Jia', element: 'Wood', god: 'Direct Officer', rank: 1 }],
          }),
          year: pillar('Bing', 'Wu', 'Fire', {
            animal: 'Horse',
            hidden_stems: [{ key: 'Ding', element: 'Fire', god: 'Indirect Resource', rank: 1 }],
          }),
        },
      }),
    });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    expect(await screen.findByRole('heading', { name: 'Four Pillars' })).toBeInTheDocument();
    expect(screen.queryByText(/The Day stem is the Day Master/)).not.toBeInTheDocument();
    expect(screen.queryByText(/month and year boundaries follow solar-term timing/)).not.toBeInTheDocument();
    expect(screen.queryByText(/The chart stays focused on stems/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Primary$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/No second snap selected/)).not.toBeInTheDocument();
    expect(screen.getAllByText('甲').length).toBeGreaterThan(0);
    expect(screen.getAllByText('子').length).toBeGreaterThan(0);
    expect(screen.getAllByText('癸').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Water / Direct Wealth').length).toBeGreaterThan(0);
    expect(screen.getByText('Root Grade')).toBeInTheDocument();
    expect(screen.getAllByText('minor root').length).toBeGreaterThan(0);
    expect(screen.getByText('De Ling')).toBeInTheDocument();
    expect(screen.getByText('resource only')).toBeInTheDocument();
    expect(screen.getByText('Resource does not fully replace a real root.')).toBeInTheDocument();
  });

  it('renders Overview as a user-facing reading without method chips in the tab body', async () => {
    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'Overview' }));

    const heading = await screen.findByRole('heading', { name: 'Reading Overview' });
    const section = heading.closest('section');
    expect(within(section).getByText('Current Reading')).toBeInTheDocument();
    expect(within(section).getAllByText('Day Master').length).toBeGreaterThan(0);
    expect(within(section).getByText('Season & Roots')).toBeInTheDocument();
    expect(within(section).getByText('Element Spread')).toBeInTheDocument();
    expect(within(section).getByText('Helpful Element Gate')).toBeInTheDocument();
    expect(within(section).getByText('candidate path')).toBeInTheDocument();
    expect(within(section).getByText('Reading Focus')).toBeInTheDocument();
    expect(within(section).queryByText('Source-Based Reading')).not.toBeInTheDocument();
    expect(within(section).queryByText('Computed rule')).not.toBeInTheDocument();
    expect(within(section).queryByText('Needs validation')).not.toBeInTheDocument();
  });

  it('uses the primary calculation sex value for profile requests', async () => {
    AstroClockAPI.getChineseAstrologyBazi
      .mockResolvedValueOnce({ success: true, data: makeProfile() })
      .mockResolvedValueOnce({ success: true, data: makeProfileWithLuck() });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await waitFor(() => expect(AstroClockAPI.getChineseAstrologyBazi).toHaveBeenCalledTimes(1));
    const primarySexGroup = screen.getByText('primary calculation sex').closest('div');
    fireEvent.click(within(primarySexGroup).getByRole('button', { name: 'primary calculation sex: Not Set' }));
    fireEvent.click(within(primarySexGroup).getByRole('option', { name: 'Female' }));

    await waitFor(() => {
      expect(AstroClockAPI.getChineseAstrologyBazi).toHaveBeenLastCalledWith(expect.objectContaining({
        snapId: 'snap-a',
        calculationSex: 'female',
        includeLuckPillars: true,
      }));
    });
  });

  it('keeps participant calculation sex separate and retains returned compatibility profiles', async () => {
    const primaryCompatibilityProfile = makeProfile({
      birth: {
        ...makeProfile().birth,
        calculation_sex: 'female',
      },
    });
    const relationshipCompatibilityProfile = makeProfile({
      source_snap_id: 'snap-b',
      snap_label: 'Relationship Example',
      birth: {
        ...makeProfile().birth,
        calculation_sex: 'male',
      },
    });
    AstroClockAPI.getChineseAstrologyCompatibility.mockResolvedValue({
      success: true,
      data: {
        primary: primaryCompatibilityProfile,
        relationship: relationshipCompatibilityProfile,
        compatibility: {
          summary: {},
          events: [],
          scoring: { relationship_context: 'general' },
          subjects: {
            primary: { source_snap_id: 'snap-a' },
            relationship: { source_snap_id: 'snap-b' },
          },
        },
      },
    });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await waitFor(() => expect(AstroClockAPI.getChineseAstrologyBazi).toHaveBeenCalledTimes(1));
    const relationshipSexControl = screen.getByLabelText('Relationship calculation sex');
    expect(relationshipSexControl).toBeDisabled();
    expect(relationshipSexControl).toHaveValue('');

    fireEvent.change(screen.getByLabelText('Relationship snap'), { target: { value: 'snap-b' } });
    await waitFor(() => expect(relationshipSexControl).toBeEnabled());
    fireEvent.change(relationshipSexControl, { target: { value: 'male' } });

    const primarySexGroup = screen.getByText('primary calculation sex').closest('div');
    fireEvent.click(within(primarySexGroup).getByRole('button', { name: 'primary calculation sex: Not Set' }));
    fireEvent.click(within(primarySexGroup).getByRole('option', { name: 'Female' }));

    await waitFor(() => {
      expect(AstroClockAPI.getChineseAstrologyCompatibility).toHaveBeenLastCalledWith(expect.objectContaining({
        primarySnapId: 'snap-a',
        relationshipSnapId: 'snap-b',
        primaryCalculationSex: 'female',
        relationshipCalculationSex: 'male',
      }));
    });
    expect(AstroClockAPI.getChineseAstrologyCompatibility.mock.calls.at(-1)[0]).not.toHaveProperty('calculationSex');

    fireEvent.click(screen.getByRole('button', { name: 'Relationships' }));
    expect(await screen.findByText('Experimental Evidence Index')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save Chinese Astrology reading locally' }));

    await waitFor(() => {
      const savedRows = JSON.parse(window.localStorage.getItem('voxstella.chineseAstrology.savedReadings.v1') || '[]');
      expect(savedRows[0].payload.compatibility_profiles.primary.birth.calculation_sex).toBe('female');
      expect(savedRows[0].payload.compatibility_profiles.relationship.birth.calculation_sex).toBe('male');
    });

    fireEvent.change(relationshipSexControl, { target: { value: 'female' } });
    fireEvent.click(within(primarySexGroup).getByRole('button', { name: 'primary calculation sex: Female' }));
    fireEvent.click(within(primarySexGroup).getByRole('option', { name: 'Male' }));
    fireEvent.click(screen.getByRole('button', { name: 'Load' }));

    await waitFor(() => {
      expect(within(primarySexGroup).getByRole('button', { name: 'primary calculation sex: Female' })).toBeInTheDocument();
      expect(relationshipSexControl).toHaveValue('male');
      const preferences = JSON.parse(window.localStorage.getItem('voxstella.chineseAstrology.preferences.v1') || '{}');
      expect(preferences.relationshipCalculationSex).toBe('male');
    });

    fireEvent.click(screen.getByRole('button', { name: 'Reset Chinese Astrology preferences' }));
    await waitFor(() => {
      expect(within(primarySexGroup).getByRole('button', { name: 'primary calculation sex: Not Set' })).toBeInTheDocument();
      expect(relationshipSexControl).toHaveValue('');
      expect(relationshipSexControl).toBeDisabled();
      const preferences = JSON.parse(window.localStorage.getItem('voxstella.chineseAstrology.preferences.v1') || '{}');
      expect(preferences.relationshipCalculationSex).toBe('');
    });
  });

  it('shows production timing layers without source evidence', async () => {
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({ success: true, data: makeProfileWithLuck() });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'Life Timing' }));

    expect(await screen.findByRole('heading', { name: 'Life Timing' })).toBeInTheDocument();
    expect(screen.queryByText(/Life Timing shows when the natal chart is activated/)).not.toBeInTheDocument();
    expect(await screen.findByText('Current Timing Layers')).toBeInTheDocument();
    expect(screen.getByText('Helpful Element Timing')).toBeInTheDocument();
    expect(screen.getByText('Decade Sequence')).toBeInTheDocument();
    expect(screen.getByText('Current 10-Year Luck')).toBeInTheDocument();
    expect(screen.getByText('Current BaZi Year')).toBeInTheDocument();
    expect(screen.getAllByText('Flowing Month').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flowing Day').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flowing Hour').length).toBeGreaterThan(0);
    expect(screen.getByText('Event Activation')).toBeInTheDocument();
    expect(screen.getByText(/Timing Window - Activation Score 9/i)).toBeInTheDocument();
    expect(screen.getByText(/Timing Window activates 3 Day or spouse-palace contacts/)).toBeInTheDocument();
    expect(screen.getByText(/Si-Hai clash marks movement during Flowing Day/)).toBeInTheDocument();
    expect(screen.queryByText(/flowing_month event trigger/)).not.toBeInTheDocument();
    expect(screen.queryByText(/flowing_day event trigger/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Day\/spouse|rescue\/arrival|pressure\/movement/)).not.toBeInTheDocument();
    expect(screen.queryByText('Timing Source Evidence')).not.toBeInTheDocument();
    expect(screen.queryByText('Rhythm Calibration')).not.toBeInTheDocument();
    expect(screen.queryByText('timing assisted finalization blocked')).not.toBeInTheDocument();
    expect(screen.queryByText('anchor.timing.luck_pillars')).not.toBeInTheDocument();
  });

  it('keeps current timing layers visible when Da Yun is unavailable', async () => {
    const profile = makeProfileWithLuck();
    profile.missing_inputs = [
      {
        field: 'calculation_sex',
        message: 'Calculation sex is required for Luck Pillars.',
      },
    ];
    profile.luck_pillars = [];
    profile.timing = {
      ...profile.timing,
      luck_pillars_enabled: false,
      direction: null,
      start_age: null,
      start_age_label: null,
      start_date: null,
      active_luck_pillar: null,
      luck_pillars: [],
      rhythm: {
        ...profile.timing.rhythm,
        layers: profile.timing.rhythm.layers.filter((layer) => layer.layer !== 'da_yun'),
      },
    };
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({ success: true, data: profile });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'Life Timing' }));

    expect(await screen.findByText('Choose calculation sex for Luck Pillars.')).toBeInTheDocument();
    expect(screen.getByText('not calculated')).toBeInTheDocument();
    expect(screen.getByText('Current Timing Layers')).toBeInTheDocument();
    expect(screen.getByText('Current BaZi Year')).toBeInTheDocument();
    expect(screen.getAllByText('Flowing Month').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flowing Day').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flowing Hour').length).toBeGreaterThan(0);
    expect(screen.getByText('Event Activation')).toBeInTheDocument();
    expect(screen.getByText('Helpful Element Timing')).toBeInTheDocument();
    expect(screen.queryByText('Current 10-Year Luck')).not.toBeInTheDocument();
    expect(screen.queryByText('Active Luck Pillar')).not.toBeInTheDocument();
    expect(screen.queryByText('Decade Sequence')).not.toBeInTheDocument();
  });

  it('shows Auxiliary Stars as marker cards without validation wording', async () => {
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({
      success: true,
      data: makeProfile({
        auxiliary_stars: {
          status: 'source_anchored_markers',
          method: 'auxiliary_stars_v1',
          source_confidence: [
            { key: 'local_source', label: 'Local source' },
            { key: 'computed_rule', label: 'Computed rule' },
          ],
          markers: [
            {
              id: 'peach_blossom',
              label: 'Peach Blossom',
              chinese: '桃花',
              pinyin: 'tao hua',
              marker_state: 'pressured',
              state_label: 'Pressured',
              reference: { label: 'Day Branch', value: 'Shen' },
              targets: [{ type: 'branch', value: 'You', label: 'You Rooster', animal: 'Rooster' }],
              target_summary: 'You Rooster',
              natal_count: 1,
              timing_count: 1,
              pressure: {
                status: 'pressured',
                event_impacts: [{ label: 'Mao-You clash', type: 'branch_clash', scope_label: 'Natal' }],
              },
              activations: [
                { layer: 'natal', pillar: 'year', pillar_label: 'Year', branch: 'You', animal: 'Rooster', domain: 'Outer world' },
                { layer: 'annual', pillar: 'annual', pillar_label: 'Current Year', branch: 'You', animal: 'Rooster', domain: 'Current BaZi year' },
              ],
              summary: 'You is the personal Peach Blossom branch for Day Branch Shen.',
              theme: 'Attraction, social visibility, charisma, and relationship timing.',
              keywords: ['attraction', 'visibility'],
            },
            {
              id: 'tian_yi',
              label: 'Tian Yi Nobleman',
              chinese: '天乙贵人',
              pinyin: 'tian yi gui ren',
              marker_state: 'quiet',
              state_label: 'Quiet',
              reference: { label: 'Day Stem', value: 'Jia' },
              targets: [
                { type: 'branch', value: 'Chou', label: 'Chou Ox', animal: 'Ox' },
                { type: 'branch', value: 'Wei', label: 'Wei Goat', animal: 'Goat' },
              ],
              target_summary: 'Chou Ox / Wei Goat',
              natal_count: 0,
              timing_count: 0,
              pressure: { status: 'clear', event_impacts: [] },
              activations: [],
              summary: 'Tian Yi Nobleman target Chou Ox / Wei Goat is calculated from Day Stem Jia.',
              theme: 'Help, guidance, support, and timely assistance themes.',
              keywords: ['support', 'guidance'],
            },
          ],
          peach_blossom: { status: 'source_based_preview', target_branch: 'You', day_branch: 'Shen' },
          notes: ['Auxiliary stars refine placement themes after the main chart is read.'],
        },
      }),
    });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'More Analysis' }));
    fireEvent.click(screen.getByRole('option', { name: 'Auxiliary Stars' }));

    expect(await screen.findByRole('heading', { name: 'Auxiliary Stars' })).toBeInTheDocument();
    expect(screen.getByText(/Shen Sha markers add named placement cues/)).toBeInTheDocument();
    expect(screen.getByText('Peach Blossom')).toBeInTheDocument();
    expect(screen.getByText('Tian Yi Nobleman')).toBeInTheDocument();
    expect(screen.getByText('You Rooster')).toBeInTheDocument();
    expect(screen.getByText('Chou Ox')).toBeInTheDocument();
    expect(screen.getByText('Wei Goat')).toBeInTheDocument();
    expect(screen.getByText('Mao-You clash')).toBeInTheDocument();
    expect(screen.queryByText(/Source-backed stars/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Needs validation/)).not.toBeInTheDocument();
    expect(screen.queryByText(/deterministic predictions/)).not.toBeInTheDocument();
  });

  it('shows Ten Gods as a contextual role map without withheld wording', async () => {
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({
      success: true,
      data: makeProfile({
        ten_gods: {
          visible: [
            {
              pillar: 'year',
              stem: 'Ren',
              factor: 'Wealth',
              factor_chinese: '財星',
              relation_chinese: '我克',
              relation_label: 'the Day Master controls this element',
              god: 'Direct Wealth',
              god_chinese: '正財',
              polarity_relation: 'opposite',
            },
          ],
          hidden: [
            {
              pillar: 'month',
              stem: 'Bing',
              rank: 1,
              factor: 'Resource',
              factor_chinese: '印梟',
              relation_chinese: '生我',
              relation_label: 'this element produces the Day Master',
              god: 'Direct Resource',
              god_chinese: '正印',
              polarity_relation: 'opposite',
            },
          ],
          factor_profile: {
            interpretation_status: 'contextual_role_map',
            summary: 'Wealth is the most visible factor. Ten God labels are read through these Five Factor families before making topic claims.',
            factors: [
              {
                factor: 'Wealth',
                chinese: '財星',
                pinyin: 'cai xing',
                relation_chinese: '我克',
                relation_label: 'the Day Master controls this element',
                domain_summary: 'Value, assets, money handling, practical management, and material responsibilities.',
                element: 'Water',
                visible_count: 1,
                hidden_count: 0,
                total_count: 1,
                layer_label: 'surface-visible',
                favorability: 'unresolved',
                functional_status: 'balanced_watch',
                status_label: 'Topic',
                gods: ['Direct Wealth'],
                keywords: ['assets', 'income'],
                summary: 'Wealth (Water) is visible on the stems, so it is easier to read as outward behavior or visible circumstance.',
                decision_basis: [],
              },
            ],
            notes: ['Visible stems describe surface expression, while hidden stems show roots.'],
            context_requirements: ['Day Master strength', 'useful-element direction', 'timing activation'],
          },
        },
      }),
    });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'More Analysis' }));
    fireEvent.click(screen.getByRole('option', { name: 'Ten Gods' }));

    expect(await screen.findByRole('heading', { name: 'Ten Gods' })).toBeInTheDocument();
    expect(screen.getByText(/Ten Gods maps visible and hidden stems to the Day Master/)).toBeInTheDocument();
    expect(screen.getByText('Role Summary')).toBeInTheDocument();
    expect(screen.getByText('Visible Stems')).toBeInTheDocument();
    expect(screen.getByText('Hidden Stems')).toBeInTheDocument();
    expect(screen.getAllByText(/Direct Wealth/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/正財/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/我克/).length).toBeGreaterThan(0);
    expect(screen.getByText('Topic')).toBeInTheDocument();
    expect(screen.queryByText(/Strength is balanced or mixed/)).not.toBeInTheDocument();
    expect(screen.queryByText(/topic evidence rather than a useful-element priority/)).not.toBeInTheDocument();
    expect(screen.queryByText(/The Day Master is the reference point/)).not.toBeInTheDocument();
    expect(screen.queryByText(/quantity is evidence, not a prediction/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Final favorability needs strength/)).not.toBeInTheDocument();
    expect(screen.queryByText('Source Preview')).not.toBeInTheDocument();
    expect(screen.queryByText(/withheld/i)).not.toBeInTheDocument();
  });

  it('shows Life Areas as source-gated topic context without withheld wording', async () => {
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({
      success: true,
      data: makeProfile({
        life_areas: {
          status: 'source_gated_context',
          method: 'bazi_life_areas_v1',
          summary: 'Career & Authority carries the clearest topic emphasis; read it through strength, useful-element direction, and timing.',
          context_requirements: [
            'Day Master strength',
            'useful-element direction',
            'pillar palace placement',
            'luck and annual activation',
          ],
          limits: [],
          areas: [
            {
              id: 'career_authority',
              label: 'Career & Authority',
              short_label: 'Career',
              context_state: 'emphasized',
              visible_factor_count: 1,
              hidden_factor_count: 1,
              relationship_contact_count: 0,
              summary: 'Career & Authority is mapped through Influence, Output and the Month, Year palace context.',
              guidance: 'This topic has chart emphasis. Treat it as a reading priority, not as a guaranteed outcome.',
              keywords: ['authority', 'status', 'visible output'],
              signals: [
                { type: 'factor', label: 'Influence', detail: 'visible 1 / hidden 1', tone: 'role' },
                { type: 'palace', label: 'Month', detail: 'formation, colleagues, and work-family structure', tone: 'placement' },
              ],
            },
            {
              id: 'health_body',
              label: 'Health & Body Balance',
              short_label: 'Body',
              context_state: 'context_required',
              visible_factor_count: 0,
              hidden_factor_count: 0,
              relationship_contact_count: 0,
              summary: 'Traditional body-balance context watches strongest element Fire x2 and lightest element Water x0. Use it as element-pattern context for the chart.',
              guidance: '',
              keywords: ['element balance', 'excess', 'deficiency'],
              signals: [
                { type: 'element', label: 'Strongest', detail: 'Fire x2', tone: 'balance' },
                { type: 'element', label: 'Lightest', detail: 'Water x0', tone: 'balance' },
              ],
            },
          ],
        },
      }),
    });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'More Analysis' }));
    fireEvent.click(screen.getByRole('option', { name: 'Life Areas' }));

    expect(await screen.findByRole('heading', { name: 'Life Areas' })).toBeInTheDocument();
    expect(screen.getByText(/Topic areas organize chart evidence/)).toBeInTheDocument();
    expect(screen.getByText('Current Topic Map')).toBeInTheDocument();
    expect(screen.getByText('Career & Authority')).toBeInTheDocument();
    expect(screen.getByText('Health & Body Balance')).toBeInTheDocument();
    expect(screen.getByText('Emphasized')).toBeInTheDocument();
    expect(screen.getByText('Context needed')).toBeInTheDocument();
    expect(screen.queryByText('Day Master strength')).not.toBeInTheDocument();
    expect(screen.queryByText(/withheld/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/unresolved/i)).not.toBeInTheDocument();
  });

  it('shows relationship contacts as a user-facing timing map', async () => {
    AstroClockAPI.getChineseAstrologyBazi.mockResolvedValue({
      success: true,
      data: makeProfileWithLuck({
        relationships: {
          summary: { total: 3, natal: 0, luck: 0, annual: 0, flowing_month: 1, flowing_day: 1, flowing_hour: 1 },
          events: [
            relationshipEvent('flowing_month', 'Flowing Month'),
            relationshipEvent('flowing_day', 'Flowing Day'),
            relationshipEvent('flowing_hour', 'Flowing Hour'),
          ],
          source_basis: 'timing contacts include current Luck, annual, flowing month, flowing day, and flowing hour layers when available',
          source_confidence: [{ key: 'computed_rule', label: 'Computed rule' }],
        },
      }),
    });

    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'Relationships' }));

    expect(await screen.findByRole('heading', { name: 'Relationships' })).toBeInTheDocument();
    expect(screen.queryByText(/Relationships shows where stem and branch contacts combine/)).not.toBeInTheDocument();
    expect(screen.getByText('Total Contacts')).toBeInTheDocument();
    expect(screen.getByText('Main Tone')).toBeInTheDocument();
    expect(screen.getByText('Day / Partner Palace')).toBeInTheDocument();
    expect(screen.getByText('Timing Contacts')).toBeInTheDocument();
    expect(screen.getAllByText('Month').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Day').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Hour').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flowing Month').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flowing Day').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Flowing Hour').length).toBeGreaterThan(0);
    expect(screen.getByText('Quiet Layers')).toBeInTheDocument();
    expect(screen.queryByText(/flowing month, flowing day, and flowing hour/)).not.toBeInTheDocument();
  });

  it('shows method notes without frontend source evidence panels', async () => {
    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'Method Notes' }));

    expect(await screen.findByRole('heading', { name: 'Method Notes' })).toBeInTheDocument();
    expect(screen.getByText('Reading Boundaries')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Technical Details' })).toBeInTheDocument();
    expect(screen.queryByText(/97 validation fixture/)).not.toBeInTheDocument();
    expect(screen.queryByText(/28 P0 gate fixture/)).not.toBeInTheDocument();
    expect(screen.queryByText('Curation Backlog')).not.toBeInTheDocument();
    expect(screen.queryByText('Advanced Rule Families')).not.toBeInTheDocument();
    expect(screen.queryByText('Needs validation')).not.toBeInTheDocument();
  });

  it('shows useful-god decision blockers without exposing raw validation chips', async () => {
    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    expect(screen.queryByRole('button', { name: 'Useful' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'More Analysis' }));
    fireEvent.click(screen.getByRole('option', { name: 'Helpful Elements' }));

    expect(await screen.findByText('Useful God Gate')).toBeInTheDocument();
    expect(screen.getAllByText('balanced withheld').length).toBeGreaterThan(0);
    expect(screen.getByText('strength not decisive')).toBeInTheDocument();
    expect(screen.getByText('final fixture not curated')).toBeInTheDocument();
    expect(screen.getByText('Decision Evidence')).toBeInTheDocument();
    expect(screen.getByText('Support / Pressure')).toBeInTheDocument();
    expect(screen.queryByText('local.destiny_code_favorable_elements')).not.toBeInTheDocument();
    expect(screen.queryByText('Source Evidence')).not.toBeInTheDocument();
    expect(screen.queryByText('release not enabled')).not.toBeInTheDocument();
    expect(screen.queryByText('Needs validation')).not.toBeInTheDocument();
  });

  it('casts the I Ching Oracle without frontend source evidence', async () => {
    render(<ChineseAstrologyPage snaps={[snapA, snapB]} snapsLoaded activeSnapId="snap-a" />);

    await screen.findByText('Four Pillars');
    fireEvent.click(screen.getByRole('button', { name: 'Switch to I Ching Oracle' }));

    expect(await screen.findByRole('heading', { name: 'I Ching Oracle' })).toBeInTheDocument();
    expect(screen.getByText('I Ching Oracle / casting memo')).toBeInTheDocument();
    expect(screen.queryByText('I Ching Oracle', { selector: 'span.opacity-55' })).not.toBeInTheDocument();
    expect(screen.queryByText('chart source')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Switch to BaZi Profile' }));
    expect(await screen.findByText('Four Pillars')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Switch to I Ching Oracle' }));
    expect(await screen.findByRole('heading', { name: 'I Ching Oracle' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Yarrow Model' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Manual Lines' }));
    fireEvent.change(screen.getByLabelText('Oracle question'), { target: { value: 'How should we proceed?' } });
    fireEvent.change(screen.getByLabelText('Oracle line 1'), { target: { value: '6' } });
    fireEvent.change(screen.getByLabelText('Oracle line 3'), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText('Oracle line 4'), { target: { value: '9' } });
    fireEvent.change(screen.getByLabelText('Oracle line 6'), { target: { value: '8' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cast Oracle' }));

    await waitFor(() => {
      expect(AstroClockAPI.getChineseAstrologyIChingOracle).toHaveBeenCalledWith(expect.objectContaining({
        question: 'How should we proceed?',
        method: 'manual',
        lines: [6, 7, 8, 9, 7, 8],
        coinValueScheme: 'heads_2_tails_3',
      }));
    });
    expect(await screen.findByText('Primary Hexagram')).toBeInTheDocument();
    expect(screen.getByText('60. Limitation')).toBeInTheDocument();
    expect(screen.getByText('Relating Hexagram')).toBeInTheDocument();
    expect(screen.getByText('47. Oppression')).toBeInTheDocument();
    expect(screen.getByText('Nuclear Hexagram')).toBeInTheDocument();
    expect(screen.getByText('50. The Cauldron')).toBeInTheDocument();
    expect(screen.getByText('Cast Input')).toBeInTheDocument();
    expect(screen.getByText('Randomness')).toBeInTheDocument();
    expect(screen.getByText('Reading Focus')).toBeInTheDocument();
    expect(screen.getByText('Zhu Xi seven-rule line focus')).toBeInTheDocument();
    expect(screen.queryByText('Oracle Source Evidence')).not.toBeInTheDocument();
    expect(screen.queryByText('public.iching_divination_method')).not.toBeInTheDocument();
  });
});
