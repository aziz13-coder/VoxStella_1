import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AstroClockAPI,
  AstroClockLicenseTokenProvider,
} from '../features/astroclock/api.mjs';


function makeJsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    headers: {
      get: () => null,
    },
  };
}

function makeBlobResponse(status, { blob = new Blob(['csv'], { type: 'text/csv' }), filename = null } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    blob: () => Promise.resolve(blob),
    text: () => Promise.resolve(''),
    headers: {
      get: (name) => {
        const key = String(name || '').toLowerCase();
        if (key === 'content-type') return blob.type || 'application/octet-stream';
        if (key === 'content-disposition' && filename) {
          return `attachment; filename="${filename}"`;
        }
        return null;
      },
    },
  };
}


describe('AstroClockAPI workflow contracts', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    AstroClockLicenseTokenProvider.invalidate();
    Object.defineProperty(window, 'API_BASE_URL', {
      configurable: true,
      writable: true,
      value: 'http://127.0.0.1:52525',
    });
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      writable: true,
      value: {
        getLicenseToken: vi.fn().mockResolvedValue('test-token'),
      },
    });
    global.fetch = vi.fn();
    global.EventSource = vi.fn(function MockEventSource(url) {
      this.url = url;
      this.close = vi.fn();
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    AstroClockLicenseTokenProvider.invalidate();
    delete window.IS_PACKAGED;
  });

  it('retries protected requests once after auth invalidation', async () => {
    window.electronAPI.getLicenseToken
      .mockResolvedValueOnce('stale-token')
      .mockResolvedValueOnce('fresh-token');
    fetch
      .mockResolvedValueOnce(makeJsonResponse(403, { detail: 'license entitlement refresh required' }))
      .mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { ok: true } }));

    const result = await AstroClockAPI.getCurrent();

    expect(result).toEqual({ success: true, data: { ok: true } });
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[1][1].headers.Authorization).toBe('Bearer fresh-token');
  });

  it('uses the configured browser-development token for strict-license requests', async () => {
    vi.stubEnv('VITE_DEV_LICENSE_TOKEN', '  astro-strict-token  ');
    window.IS_PACKAGED = false;
    delete window.electronAPI;
    fetch.mockResolvedValueOnce(
      makeJsonResponse(200, { success: true, data: { ok: true } })
    );

    await AstroClockAPI.getTraitProfile();

    expect(fetch.mock.calls[0][1].headers.Authorization).toBe(
      'Bearer astro-strict-token'
    );
  });

  it('omits fake bearer credentials when browser development uses backend bypass', async () => {
    vi.stubEnv('VITE_DEV_LICENSE_TOKEN', '');
    window.IS_PACKAGED = false;
    delete window.electronAPI;
    fetch.mockResolvedValueOnce(
      makeJsonResponse(200, { success: true, data: { ok: true } })
    );

    await AstroClockAPI.getTraitProfile();

    expect(fetch.mock.calls[0][1].headers).not.toHaveProperty('Authorization');
  });

  it('preserves manual chart context in current requests', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { ok: true } }));

    await AstroClockAPI.getCurrent({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const url = new URL(fetch.mock.calls[0][0]);
    expect(url.pathname).toBe('/api/astro-clock/current');
    expect(url.searchParams.get('mode')).toBe('manual');
    expect(url.searchParams.get('datetime')).toBe('2026-03-22T06:32:00');
    expect(url.searchParams.get('location')).toBe('Israel');
    expect(url.searchParams.get('timezone')).toBe('Asia/Jerusalem');
    expect(url.searchParams.get('latitude')).toBe('31.778');
    expect(url.searchParams.get('longitude')).toBe('35.235');
    expect(url.searchParams.get('house_system_code')).toBe('R');
  });

  it('posts Chinese Astrology BaZi requests with saved snap context', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { source_snap_id: 'snap-bazi' } }));

    const result = await AstroClockAPI.getChineseAstrologyBazi({
      snapId: 'snap-bazi',
      calculationSex: 'female',
      includeLuckPillars: true,
      useTrueSolarTime: true,
      dayBoundaryRule: 'true_solar_midnight',
      hourPillarVariant: 'late_zi_next_day',
      luckDirectionRule: 'day_stem_polarity',
    });

    expect(result).toEqual({ success: true, data: { source_snap_id: 'snap-bazi' } });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/chinese-astrology/bazi');
    expect(fetch.mock.calls[0][1].method).toBe('POST');
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.snap_id).toBe('snap-bazi');
    expect(body.calculation_sex).toBe('female');
    expect(body.include_luck_pillars).toBe(true);
    expect(body.use_true_solar_time).toBe(true);
    expect(body.day_boundary_rule).toBe('true_solar_midnight');
    expect(body.hour_pillar_variant).toBe('late_zi_next_day');
    expect(body.luck_direction_rule).toBe('day_stem_polarity');
  });

  it('posts Chinese Astrology compatibility requests with two saved snaps', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { compatibility: { method: 'bazi_pair_relationship_codes_v1' } } }));

    const result = await AstroClockAPI.getChineseAstrologyCompatibility({
      primarySnapId: 'snap-a',
      relationshipSnapId: 'snap-b',
      relationshipContext: 'romantic',
      calculationSex: 'female',
      useTrueSolarTime: true,
      dayBoundaryRule: 'civil_midnight',
      hourPillarVariant: 'standard_zi_hour',
      luckDirectionRule: 'year_branch_polarity',
    });

    expect(result).toEqual({ success: true, data: { compatibility: { method: 'bazi_pair_relationship_codes_v1' } } });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/chinese-astrology/compatibility');
    expect(fetch.mock.calls[0][1].method).toBe('POST');
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.primary_snap_id).toBe('snap-a');
    expect(body.relationship_snap_id).toBe('snap-b');
    expect(body.relationship_context).toBe('romantic');
    expect(body.calculation_sex).toBe('female');
    expect(body.include_luck_pillars).toBe(true);
    expect(body.use_true_solar_time).toBe(true);
    expect(body.day_boundary_rule).toBe('civil_midnight');
    expect(body.hour_pillar_variant).toBe('standard_zi_hour');
    expect(body.luck_direction_rule).toBe('year_branch_polarity');
  });

  it('posts participant-specific calculation sex for Chinese Astrology compatibility', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, {
      success: true,
      data: {
        primary: { birth: { calculation_sex: 'female' } },
        relationship: { birth: { calculation_sex: 'male' } },
        compatibility: {},
      },
    }));

    await AstroClockAPI.getChineseAstrologyCompatibility({
      primarySnapId: 'snap-a',
      relationshipSnapId: 'snap-b',
      primaryCalculationSex: 'female',
      relationshipCalculationSex: 'male',
    });

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.primary_calculation_sex).toBe('female');
    expect(body.relationship_calculation_sex).toBe('male');
    expect(body).not.toHaveProperty('calculation_sex');
  });

  it('posts I Ching Oracle cast requests with manual lines and source options', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { oracle: { method: 'iching_oracle_v1' } } }));

    const result = await AstroClockAPI.getChineseAstrologyIChingOracle({
      question: 'How should we proceed?',
      method: 'manual',
      lines: [6, 7, 8, 9, 7, 8],
      coinValueScheme: 'heads_2_tails_3',
    });

    expect(result).toEqual({ success: true, data: { oracle: { method: 'iching_oracle_v1' } } });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/chinese-astrology/iching-oracle');
    expect(fetch.mock.calls[0][1].method).toBe('POST');
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.question).toBe('How should we proceed?');
    expect(body.method).toBe('manual');
    expect(body.lines).toEqual([6, 7, 8, 9, 7, 8]);
    expect(body.coin_value_scheme).toBe('heads_2_tails_3');
  });

  it('posts I Ching Oracle yarrow model requests with optional seed', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { oracle: { casting_method: 'yarrow_probability' } } }));

    await AstroClockAPI.getChineseAstrologyIChingOracle({
      question: 'What is changing underneath?',
      method: 'yarrow',
      seed: 'fixture-yarrow',
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.question).toBe('What is changing underneath?');
    expect(body.method).toBe('yarrow');
    expect(body.seed).toBe('fixture-yarrow');
    expect(body.lines).toBeUndefined();
  });

  it('posts Birth Certification rectification requests to the certification endpoint', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { certification: { status: 'insufficient_data' } } }));

    const body = {
      birth: {
        date: '1990-01-01',
        latitude: 31.778,
        longitude: 35.235,
        timezone: 'Asia/Jerusalem',
      },
      search: { start_time: '00:00', end_time: '23:59' },
      events: [
        {
          label: 'Documented milestone',
          timestamp: '2020-01-01T12:00:00+02:00',
          latitude: 32.0809,
          longitude: 34.7806,
          precision: 2,
        },
      ],
    };

    const result = await AstroClockAPI.rectifyBirthTime(body);

    expect(result).toEqual({ success: true, data: { certification: { status: 'insufficient_data' } } });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/certification/rectify');
    expect(fetch.mock.calls[0][1].method).toBe('POST');
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(body);
  });

  it('propagates election stream ticket failures to the caller', async () => {
    window.electronAPI.getLicenseToken
      .mockResolvedValueOnce('stale-token')
      .mockResolvedValueOnce('fresh-token');
    fetch
      .mockResolvedValueOnce(
        makeJsonResponse(403, { detail: 'license entitlement refresh required' })
      )
      .mockResolvedValueOnce(
        makeJsonResponse(403, { detail: 'license entitlement refresh required' })
      );

    await expect(
      AstroClockAPI.electionStream({
        matter: 'marriage',
        start: '2026-03-08T00:00:00Z',
        end: '2026-03-08T01:00:00Z',
        location: 'Jerusalem',
      })
    ).rejects.toThrow('license entitlement refresh required');
  });

  it('serializes election stream workflow options into the ticketed path', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-123' }));

    const es = await AstroClockAPI.electionStream({
      matter: 'contract',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T02:00:00Z',
      location: 'Jerusalem',
      timezone: 'Asia/Jerusalem',
      houseSystem: 'R',
      stepMinutes: 15,
      limit: 5,
      includeSrLr: true,
      weekdays: ['Mon', 'Thu'],
      hourStart: 9,
      hourEnd: 17,
      natalSnapId: 'snap-1',
      natalDatetime: '1990-01-01T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'UTC',
      gender: 'male',
      hairGoal: 'growth',
      surgerySign: 'Aries',
      procedure: 'cutting',
      includeLunationScreen: true,
      includeFixedStars: true,
      includeTraditionalTiming: true,
      businessMode: 'growth',
      emphasizeCommerce: true,
      journeyType: 'short',
      legalAction: 'filing',
      actionType: 'attack',
      bodyParts: ['cheeks', 'lips'],
      bodySigns: ['Libra', 'Taurus'],
      procedureType: 'fillers',
      preferFixedAsc: true,
      saturnBindingOk: false,
      minMercuryDirectDays: 3,
      contractMode: 'new',
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/stream-ticket');

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('/api/astro-clock/election/suggest/stream?');
    expect(body.path).toContain('matter=contract');
    expect(body.path).toContain('house_system_code=R');
    expect(body.path).toContain('step_minutes=15');
    expect(body.path).toContain('include_sr_lr=1');
    expect(body.path).toContain('weekday=mon');
    expect(body.path).toContain('weekday=thu');
    expect(body.path).toContain('natal_snap_id=snap-1');
    expect(body.path).toContain('natal_datetime=1990-01-01T00%3A00%3A00Z');
    expect(body.path).toContain('natal_location=Jerusalem');
    expect(body.path).toContain('natal_timezone=UTC');
    expect(body.path).not.toContain('gender=male');
    expect(body.path).toContain('hair_goal=growth');
    expect(body.path).toContain('surgery_sign=Aries');
    expect(body.path).toContain('include_lunation_screen=1');
    expect(body.path).toContain('include_fixed_stars=1');
    expect(body.path).toContain('include_traditional_timing=1');
    expect(body.path).toContain('business_mode=growth');
    expect(body.path).toContain('emphasize_commerce=1');
    expect(body.path).toContain('journey_type=short');
    expect(body.path).toContain('legal_action=filing');
    expect(body.path).toContain('action_type=attack');
    expect(body.path).toContain('body_parts=cheeks%2Clips');
    expect(body.path).toContain('body_signs=Libra%2CTaurus');
    expect(body.path).toContain('procedure_type=fillers');
    expect(body.path).toContain('prefer_fixed_asc=1');
    expect(body.path).toContain('saturn_binding_ok=0');
    expect(body.path).toContain('min_mercury_direct_days=3');
    expect(body.path).toContain('contract_mode=new');

    expect(es.url).toBe(
      'http://127.0.0.1:52525/api/astro-clock/election/suggest/stream?matter=contract&start=2026-03-08T00%3A00%3A00Z&end=2026-03-08T02%3A00%3A00Z&location=Jerusalem&timezone=Asia%2FJerusalem&house_system_code=R&step_minutes=15&limit=5&include_sr_lr=1&weekday=mon&weekday=thu&hour_start=9&hour_end=17&natal_snap_id=snap-1&natal_datetime=1990-01-01T00%3A00%3A00Z&natal_location=Jerusalem&natal_timezone=UTC&hair_goal=growth&surgery_sign=Aries&procedure=cutting&include_lunation_screen=1&include_fixed_stars=1&include_traditional_timing=1&business_mode=growth&emphasize_commerce=1&journey_type=short&legal_action=filing&action_type=attack&body_parts=cheeks%2Clips&body_signs=Libra%2CTaurus&procedure_type=fillers&prefer_fixed_asc=1&saturn_binding_ok=0&min_mercury_direct_days=3&contract_mode=new&stream_ticket=ticket-123'
    );
  });

  it('serializes beta marriage election parameters into the ticketed path', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-beta' }));

    const es = await AstroClockAPI.electionStream({
      matter: 'marriage',
      marriageAlgorithm: 'beta',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T02:00:00Z',
      location: 'Jerusalem',
      participantASnapId: 'snap-a',
      participantBSnapId: 'snap-b',
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('matter=marriage');
    expect(body.path).toContain('marriage_algorithm=beta');
    expect(body.path).toContain('participant_a_snap_id=snap-a');
    expect(body.path).toContain('participant_b_snap_id=snap-b');
    expect(es.url).toContain('marriage_algorithm=beta');
    expect(es.url).toContain('participant_a_snap_id=snap-a');
    expect(es.url).toContain('participant_b_snap_id=snap-b');
    expect(es.url).toContain('stream_ticket=ticket-beta');
  });

  it('serializes beta business participant lists into the ticketed path', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-business-beta' }));

    const es = await AstroClockAPI.electionStream({
      matter: 'business',
      businessAlgorithm: 'beta',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T02:00:00Z',
      location: 'Jerusalem',
      participantSnapIds: ['snap-founder-a', 'snap-founder-b', 'snap-founder-c'],
      businessBetaDisplayMode: 'detail',
      businessBetaScope: 'selected',
      businessBetaCurrentLineId: 'participant:1',
      businessBetaSelectedLineIds: ['event', 'participant:1'],
      businessBetaLevelPercent: 72,
      businessMode: 'growth',
      emphasizeCommerce: true,
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('matter=business');
    expect(body.path).toContain('business_algorithm=beta');
    expect(body.path).toContain('participant_snap_id=snap-founder-a');
    expect(body.path).toContain('participant_snap_id=snap-founder-b');
    expect(body.path).toContain('participant_snap_id=snap-founder-c');
    expect(body.path).toContain('business_beta_display_mode=detail');
    expect(body.path).toContain('business_beta_scope=selected');
    expect(body.path).toContain('business_beta_current_line_id=participant%3A1');
    expect(body.path).toContain('business_beta_selected_line_id=event');
    expect(body.path).toContain('business_beta_selected_line_id=participant%3A1');
    expect(body.path).toContain('business_beta_level_percent=72');
    expect(body.path).toContain('business_mode=growth');
    expect(body.path).toContain('emphasize_commerce=1');
    expect(es.url).toContain('business_algorithm=beta');
    expect(es.url).toContain('participant_snap_id=snap-founder-a');
    expect(es.url).toContain('participant_snap_id=snap-founder-b');
    expect(es.url).toContain('participant_snap_id=snap-founder-c');
    expect(es.url).toContain('business_beta_display_mode=detail');
    expect(es.url).toContain('business_beta_scope=selected');
    expect(es.url).toContain('business_beta_current_line_id=participant%3A1');
    expect(es.url).toContain('business_beta_selected_line_id=event');
    expect(es.url).toContain('business_beta_selected_line_id=participant%3A1');
    expect(es.url).toContain('business_beta_level_percent=72');
    expect(es.url).toContain('stream_ticket=ticket-business-beta');
  });

  it('serializes estate election parameters into the ticketed path', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-estate' }));

    const es = await AstroClockAPI.electionStream({
      matter: 'estate',
      estateDirection: 'sell',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T02:00:00Z',
      location: 'Jerusalem',
      estateParticipantSnapId: 'snap-estate',
      estateDisplayMode: 'detail',
      estateScope: 'selected',
      estateCurrentLineId: 'participant:1',
      estateSelectedLineIds: ['event', 'participant:1'],
      estateLevelPercent: 75,
      includeTraditionalTiming: true,
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('matter=estate');
    expect(body.path).toContain('estate_direction=sell');
    expect(body.path).toContain('estate_participant_snap_id=snap-estate');
    expect(body.path).toContain('estate_display_mode=detail');
    expect(body.path).toContain('estate_scope=selected');
    expect(body.path).toContain('estate_current_line_id=participant%3A1');
    expect(body.path).toContain('estate_selected_line_id=event');
    expect(body.path).toContain('estate_selected_line_id=participant%3A1');
    expect(body.path).toContain('estate_level_percent=75');
    expect(body.path).toContain('include_traditional_timing=1');
    expect(es.url).toContain('matter=estate');
    expect(es.url).toContain('estate_direction=sell');
    expect(es.url).toContain('estate_participant_snap_id=snap-estate');
    expect(es.url).toContain('estate_display_mode=detail');
    expect(es.url).toContain('estate_scope=selected');
    expect(es.url).toContain('estate_current_line_id=participant%3A1');
    expect(es.url).toContain('estate_selected_line_id=event');
    expect(es.url).toContain('estate_selected_line_id=participant%3A1');
    expect(es.url).toContain('estate_level_percent=75');
    expect(es.url).toContain('stream_ticket=ticket-estate');
  });

  it('serializes lunar fertility election parameters without conception gender leakage', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-lunar' }));

    const es = await AstroClockAPI.electionStream({
      matter: 'lunar_fertility',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-10T00:00:00Z',
      location: 'Jerusalem',
      natalSnapId: 'snap-natal',
      considerMode: 'phase_and_antiphase',
      levelPercent: 33,
      gender: 'male',
    });

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('matter=lunar_fertility');
    expect(body.path).toContain('natal_snap_id=snap-natal');
    expect(body.path).toContain('consider_mode=phase_and_antiphase');
    expect(body.path).toContain('level_percent=33');
    expect(body.path).not.toContain('gender=male');
    expect(es.url).toContain('matter=lunar_fertility');
    expect(es.url).toContain('consider_mode=phase_and_antiphase');
    expect(es.url).toContain('level_percent=33');
    expect(es.url).toContain('stream_ticket=ticket-lunar');
  });

  it('keeps conception gender serialization on the conception model only', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-conception' }));

    await AstroClockAPI.electionStream({
      matter: 'conception',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T02:00:00Z',
      location: 'Jerusalem',
      gender: 'female',
    });

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('matter=conception');
    expect(body.path).toContain('gender=female');
  });

  it('serializes explicit none weekdays and minute-precision hour filters', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-time' }));

    const es = await AstroClockAPI.electionStream({
      matter: 'marriage',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T02:00:00Z',
      location: 'Jerusalem',
      weekdayMode: 'none',
      weekdays: [],
      hourStart: '09:30',
      hourEnd: '17:30',
    });

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('weekday_mode=none');
    expect(body.path).not.toContain('weekday=');
    expect(body.path).toContain('hour_start=09%3A30');
    expect(body.path).toContain('hour_end=17%3A30');
    expect(es.url).toContain('weekday_mode=none');
    expect(es.url).toContain('hour_start=09%3A30');
    expect(es.url).toContain('hour_end=17%3A30');
  });

  it('serializes validation requests with the same election workflow options', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true }));

    await AstroClockAPI.validateElection({
      matter: 'contract',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T02:00:00Z',
      location: 'Jerusalem',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
      stepMinutes: 15,
      limit: 5,
      includeSrLr: true,
      weekdays: ['Mon', 'Thu'],
      hourStart: 9,
      hourEnd: 17,
      natalSnapId: 'snap-1',
      natalDatetime: '1990-01-01T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'UTC',
      gender: 'male',
      hairGoal: 'growth',
      surgerySign: 'Aries',
      procedure: 'cutting',
      includeLunationScreen: true,
      includeFixedStars: true,
      includeTraditionalTiming: true,
      businessMode: 'growth',
      emphasizeCommerce: true,
      journeyType: 'short',
      legalAction: 'filing',
      actionType: 'attack',
      bodyParts: ['cheeks', 'lips'],
      bodySigns: ['Libra', 'Taurus'],
      procedureType: 'fillers',
      preferFixedAsc: true,
      saturnBindingOk: false,
      minMercuryDirectDays: 3,
      contractMode: 'new',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/election/validate?');
    expect(url).toContain('matter=contract');
    expect(url).toContain('location=Jerusalem');
    expect(url).toContain('timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
    expect(url).toContain('house_system_code=R');
    expect(url).toContain('step_minutes=15');
    expect(url).toContain('include_sr_lr=1');
    expect(url).toContain('weekday=mon');
    expect(url).toContain('weekday=thu');
    expect(url).toContain('natal_snap_id=snap-1');
    expect(url).toContain('natal_datetime=1990-01-01T00%3A00%3A00Z');
    expect(url).toContain('natal_location=Jerusalem');
    expect(url).toContain('natal_timezone=UTC');
    expect(url).not.toContain('gender=male');
    expect(url).toContain('hair_goal=growth');
    expect(url).toContain('surgery_sign=Aries');
    expect(url).toContain('include_lunation_screen=1');
    expect(url).toContain('include_fixed_stars=1');
    expect(url).toContain('include_traditional_timing=1');
    expect(url).toContain('business_mode=growth');
    expect(url).toContain('emphasize_commerce=1');
    expect(url).toContain('journey_type=short');
    expect(url).toContain('legal_action=filing');
    expect(url).toContain('action_type=attack');
    expect(url).toContain('body_parts=cheeks%2Clips');
    expect(url).toContain('body_signs=Libra%2CTaurus');
    expect(url).toContain('procedure_type=fillers');
    expect(url).toContain('prefer_fixed_asc=1');
    expect(url).toContain('saturn_binding_ok=0');
    expect(url).toContain('min_mercury_direct_days=3');
    expect(url).toContain('contract_mode=new');
  });

  it('does not emit dead compass query parameters', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getCompass({ origin: '31.0,35.0', includeModern: true });

    expect(fetch.mock.calls[0][0]).toBe(
      'http://127.0.0.1:52525/api/astro-clock/compass?include_modern=1'
    );
  });

  it('serializes Directional 3D requests with explicit chart context', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getDirectional3d({
      includeModern: true,
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/directional-3d?');
    expect(url).toContain('include_modern=1');
    expect(url).toContain('mode=manual');
    expect(url).toContain('datetime=2026-03-22T06%3A32%3A00');
    expect(url).toContain('location=Israel');
    expect(url).toContain('timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
    expect(url).toContain('house_system_code=R');
  });

  it('serializes receptions requests with explicit chart context', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getReceptions({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/receptions?');
    expect(url).toContain('mode=manual');
    expect(url).toContain('datetime=2026-03-22T06%3A32%3A00');
    expect(url).toContain('location=Israel');
    expect(url).toContain('timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
    expect(url).toContain('house_system_code=R');
  });

  it('does not emit dead auto-context query parameters', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getAutoContext({
      natalDatetime: '2026-03-08T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
      residenceLocation: 'Tel Aviv',
      srWindowDays: 3,
      anchorCenter: '2026-03-08T12:00:00Z',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).not.toContain('residence_location');
    expect(url).not.toContain('sr_window_days');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
  });

  it('does not emit dead transit window metadata parameters', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getTransitsWindow({
      natalDatetime: '2026-03-08T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'Asia/Jerusalem',
      houseSystem: 'R',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T06:00:00Z',
      pdLabel: 'PD',
      pdSig: 'Sun',
      pdPro: 'Mars',
      pdAspect: 'Square',
      pdType: 'primary',
      saLabel: 'SA',
      includeLunationScreen: true,
      includeFixedStars: true,
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).not.toContain('pd_label');
    expect(url).not.toContain('pd_sig');
    expect(url).not.toContain('pd_pro');
    expect(url).not.toContain('pd_aspect');
    expect(url).not.toContain('pd_type');
    expect(url).not.toContain('sa_label');
    expect(url).not.toContain('include_lunation_screen');
    expect(url).not.toContain('include_fixed_stars');
  });

  it('serializes single-transit requests with house system and filters', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getTransits({
      natalSnapId: 'snap-1',
      houseSystem: 'W',
      transitDatetime: '2026-03-08T12:00:00Z',
      includeModern: true,
      includeNatalModern: true,
      includeCusps: true,
      includeAntiscia: true,
      includeLots: true,
      focusHouses: [10],
      focusPlanets: ['Saturn'],
      sensitiveHouses: [4],
      sensitivePlanets: ['Moon'],
      transiting: ['Saturn'],
      natal: ['Sun'],
      aspects: ['Square'],
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/transits?');
    expect(url).toContain('natal_snap_id=snap-1');
    expect(url).toContain('house_system_code=W');
    expect(url).toContain('transit_datetime=2026-03-08T12%3A00%3A00Z');
    expect(url).toContain('include_modern=1');
    expect(url).toContain('include_natal_modern=1');
    expect(url).toContain('include_cusps=1');
    expect(url).toContain('include_antiscia=1');
    expect(url).toContain('include_lots=1');
    expect(url).toContain('focus_house=10');
    expect(url).toContain('focus_planet=Saturn');
    expect(url).toContain('sensitive_house=4');
    expect(url).toContain('sensitive_planet=Moon');
    expect(url).toContain('transiting=Saturn');
    expect(url).toContain('natal=Sun');
    expect(url).toContain('aspect=Square');
  });

  it('serializes manual transit natal coordinates', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getTransits({
      natalDatetime: '2026-03-08T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
      transitDatetime: '2026-03-08T12:00:00Z',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/transits?');
    expect(url).toContain('natal_datetime=2026-03-08T00%3A00%3A00Z');
    expect(url).toContain('natal_location=Jerusalem');
    expect(url).toContain('natal_timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
  });

  it('serializes transit stream requests into a ticketed path', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, ticket: 'ticket-456' }));

    const es = await AstroClockAPI.createTransitsWindowStream({
      natalDatetime: '1990-01-01T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'UTC',
      houseSystem: 'E',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T06:00:00Z',
      stepMinutes: 30,
      includeModern: true,
      includeNatalModern: true,
      includeCusps: true,
      includeAntiscia: true,
      includeLots: true,
      focusHouses: [10],
      focusPlanets: ['Jupiter'],
      sensitiveHouses: [4],
      sensitivePlanets: ['Moon'],
      pdStart: '2026-03-08T01:00:00Z',
      pdEnd: '2026-03-08T03:00:00Z',
      transiting: ['Saturn'],
      natal: ['Sun'],
      aspects: ['Square'],
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/stream-ticket');

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.path).toContain('/api/astro-clock/transits/window/stream?');
    expect(body.path).toContain('house_system_code=E');
    expect(body.path).toContain('start=2026-03-08T00%3A00%3A00Z');
    expect(body.path).toContain('end=2026-03-08T06%3A00%3A00Z');
    expect(body.path).toContain('step_minutes=30');
    expect(body.path).toContain('include_modern=1');
    expect(body.path).toContain('include_natal_modern=1');
    expect(body.path).toContain('include_cusps=1');
    expect(body.path).toContain('include_antiscia=1');
    expect(body.path).toContain('include_lots=1');
    expect(body.path).toContain('focus_house=10');
    expect(body.path).toContain('focus_planet=Jupiter');
    expect(body.path).toContain('sensitive_house=4');
    expect(body.path).toContain('sensitive_planet=Moon');
    expect(body.path).toContain('pd_start=2026-03-08T01%3A00%3A00Z');
    expect(body.path).toContain('pd_end=2026-03-08T03%3A00%3A00Z');
    expect(body.path).toContain('transiting=Saturn');
    expect(body.path).toContain('natal=Sun');
    expect(body.path).toContain('aspect=Square');

    expect(es.url).toContain('/api/astro-clock/transits/window/stream?');
    expect(es.url).toContain('house_system_code=E');
    expect(es.url).toContain('stream_ticket=ticket-456');
  });

  it('skips transit stream ticket requests when no license token is available', async () => {
    window.electronAPI.getLicenseToken.mockResolvedValueOnce(null);

    const es = await AstroClockAPI.createTransitsWindowStream({
      natalDatetime: '1990-01-01T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'UTC',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T06:00:00Z',
      stepMinutes: 30,
    });

    expect(es).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('serializes predictor requests with observer context and context windows', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

    try {
      await AstroClockAPI.getPredictions({
        natalSnapId: 'snap-2',
        houseSystem: 'P',
        start: '2026-03-08T00:00:00Z',
        end: '2026-03-08T12:00:00Z',
        stepMinutes: 30,
        location: 'Tokyo',
        timezone: 'Asia/Tokyo',
        limit: 12,
        includeSeries: true,
        includeModern: true,
        includeNatalModern: true,
        includeCusps: true,
        includeAntiscia: true,
        includeLots: true,
        focusHouses: [10],
        focusPlanets: ['Jupiter'],
        sensitiveHouses: [4],
        sensitivePlanets: ['Moon'],
        pdStart: '2026-03-08T01:00:00Z',
        pdEnd: '2026-03-08T03:00:00Z',
        progStart: '2026-03-08T02:00:00Z',
        progEnd: '2026-03-08T04:00:00Z',
        saStart: '2026-03-08T05:00:00Z',
        saEnd: '2026-03-08T07:00:00Z',
        sigBeta: true,
      });

      const url = String(fetch.mock.calls[0][0]);
      expect(url).toContain('/api/astro-clock/predictor?');
      expect(url).toContain('natal_snap_id=snap-2');
      expect(url).toContain('house_system_code=P');
      expect(url).toContain('location=Tokyo');
      expect(url).toContain('timezone=Asia%2FTokyo');
      expect(url).toContain('include_series=1');
      expect(url).toContain('limit=12');
      expect(url).toContain('pd_start=2026-03-08T01%3A00%3A00Z');
      expect(url).toContain('prog_start=2026-03-08T02%3A00%3A00Z');
      expect(url).toContain('sa_start=2026-03-08T05%3A00%3A00Z');
      expect(url).toContain('sig_beta=1');
      expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 90000);
    } finally {
      setTimeoutSpy.mockRestore();
    }
  });

  it('serializes single-transit CSV exports with the active house system', async () => {
    fetch.mockResolvedValueOnce(
      makeBlobResponse(200, { filename: 'transits.csv', blob: new Blob(['x'], { type: 'text/csv' }) })
    );

    const exported = await AstroClockAPI.exportTransits({
      natalSnapId: 'snap-3',
      houseSystem: 'W',
      transitDatetime: '2026-03-08T12:00:00Z',
      includeModern: true,
      includeCusps: true,
      transiting: ['Saturn'],
      aspects: ['Square'],
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/transits/export?');
    expect(url).toContain('natal_snap_id=snap-3');
    expect(url).toContain('house_system_code=W');
    expect(url).toContain('transit_datetime=2026-03-08T12%3A00%3A00Z');
    expect(url).toContain('include_modern=1');
    expect(url).toContain('include_cusps=1');
    expect(url).toContain('transiting=Saturn');
    expect(url).toContain('aspect=Square');
    expect(exported.filename).toBe('transits.csv');
  });

  it('serializes transit-window CSV exports with context windows', async () => {
    fetch.mockResolvedValueOnce(
      makeBlobResponse(200, { filename: 'transits_window.csv', blob: new Blob(['x'], { type: 'text/csv' }) })
    );

    const exported = await AstroClockAPI.exportTransitsWindow({
      natalDatetime: '1990-01-01T00:00:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'UTC',
      houseSystem: 'E',
      start: '2026-03-08T00:00:00Z',
      end: '2026-03-08T06:00:00Z',
      stepMinutes: 30,
      includeModern: true,
      includeCusps: true,
      pdStart: '2026-03-08T01:00:00Z',
      pdEnd: '2026-03-08T03:00:00Z',
      saStart: '2026-03-08T05:00:00Z',
      saEnd: '2026-03-08T07:00:00Z',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/transits/window/export?');
    expect(url).toContain('natal_datetime=1990-01-01T00%3A00%3A00Z');
    expect(url).toContain('natal_location=Jerusalem');
    expect(url).toContain('natal_timezone=UTC');
    expect(url).toContain('house_system_code=E');
    expect(url).toContain('pd_start=2026-03-08T01%3A00%3A00Z');
    expect(url).toContain('pd_end=2026-03-08T03%3A00%3A00Z');
    expect(url).toContain('sa_start=2026-03-08T05%3A00%3A00Z');
    expect(url).toContain('sa_end=2026-03-08T07%3A00%3A00Z');
    expect(exported.filename).toBe('transits_window.csv');
  });

  it('preserves manual chart context in dashboard requests', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getDashboard({
      includeModern: true,
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      houseSystem: 'R',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/dashboard?');
    expect(url).toContain('include_modern=1');
    expect(url).toContain('mode=manual');
    expect(url).toContain('datetime=2026-03-22T06%3A32%3A00');
    expect(url).toContain('location=Israel');
    expect(url).toContain('timezone=Asia%2FJerusalem');
    expect(url).toContain('house_system_code=R');
  });

  it('preserves manual chart coordinates in mode requests', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true }));

    await AstroClockAPI.setMode({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    const [, requestInit] = fetch.mock.calls[0];
    const body = JSON.parse(requestInit.body);
    expect(body).toMatchObject({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      house_system: 'R',
      house_system_code: 'R',
    });
  });

  it('preserves chart context and core timeout in snap requests', async () => {
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { id: 'snap-1' } }));

    try {
      await AstroClockAPI.createSnap({
        label: 'Snap',
        includeModern: true,
        specialDegrees: ['25 Leo'],
        mode: 'manual',
        datetime: '2026-03-22T06:32:00',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
        houseSystem: 'R',
        certification: {
          kind: 'birth_time_certification',
          status: 'rectified_candidate',
          confidence: 'medium',
          selected_candidate: {
            timestamp: '2026-03-22T06:32:00',
            strength: 88.4,
          },
        },
        dashboard: {
          timestamp: '2026-03-22T04:32:00Z',
          location: 'Israel',
          timezone: 'Asia/Jerusalem',
          planets: [{ planet: 'Moon', sign: 'Virgo' }],
        },
      });

      const [url, requestInit] = fetch.mock.calls[0];
      const body = JSON.parse(requestInit.body);
      expect(String(url)).toBe('http://127.0.0.1:52525/api/astro-clock/snap');
      expect(body).toMatchObject({
        label: 'Snap',
        include_modern: true,
        special_degrees: ['25 Leo'],
        mode: 'manual',
        datetime: '2026-03-22T06:32:00',
        location: 'Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
        house_system: 'R',
        house_system_code: 'R',
        certification: {
          kind: 'birth_time_certification',
          status: 'rectified_candidate',
          confidence: 'medium',
          selected_candidate: {
            timestamp: '2026-03-22T06:32:00',
            strength: 88.4,
          },
        },
        dashboard: {
          timestamp: '2026-03-22T04:32:00Z',
          location: 'Israel',
          timezone: 'Asia/Jerusalem',
          planets: [{ planet: 'Moon', sign: 'Virgo' }],
        },
      });
      expect(setTimeoutSpy.mock.calls.some(([, timeout]) => timeout === 90000)).toBe(true);
    } finally {
      setTimeoutSpy.mockRestore();
    }
  });

  it('uses an extended timeout for Astro Clock core dashboard requests', async () => {
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');
    fetch
      .mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }))
      .mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }))
      .mockResolvedValueOnce(makeJsonResponse(200, { success: true }));

    try {
      await AstroClockAPI.getDashboard({ mode: 'manual', datetime: '2026-03-22T06:32:00', location: 'Israel' });
      await AstroClockAPI.getPlanetaryHours({ mode: 'manual', datetime: '2026-03-22T06:32:00', location: 'Israel' });
      await AstroClockAPI.setMode({ mode: 'manual', datetime: '2026-03-22T06:32:00', location: 'Israel' });

      const ninetySecondTimeoutCalls = setTimeoutSpy.mock.calls.filter(([, timeout]) => timeout === 90000);
      expect(ninetySecondTimeoutCalls.length).toBeGreaterThanOrEqual(3);
    } finally {
      setTimeoutSpy.mockRestore();
    }
  });

  it('preserves manual chart context in trait profile requests', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getTraitProfile({
      specialDegrees: ['25 Leo'],
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/traits/profile?');
    expect(url).toContain('special_degree=25+Leo');
    expect(url).toContain('mode=manual');
    expect(url).toContain('datetime=2026-03-22T06%3A32%3A00');
    expect(url).toContain('location=Israel');
    expect(url).toContain('timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
    expect(url).toContain('house_system_code=R');
  });

  it('preserves manual chart context in degree hit points requests', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { points: [] } }));

    await AstroClockAPI.getDegreeHitPoints({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
      sexCode: 2,
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/points/degree-hits?');
    expect(url).toContain('mode=manual');
    expect(url).toContain('datetime=2026-03-22T06%3A32%3A00');
    expect(url).toContain('location=Israel');
    expect(url).toContain('timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
    expect(url).toContain('house_system_code=R');
    expect(url).toContain('sex_code=2');
  });

  it('preserves manual chart context in forensic requests', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, features: {} }));

    await AstroClockAPI.getForensic({
      mode: 'manual',
      datetime: '2026-03-22T06:32:00',
      location: 'Israel',
      timezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
      caseType: 'child',
      abduction: true,
      origin: '31.7683,35.2137',
      line_zones: true,
      corridor_deg: 7,
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/forensic?');
    expect(url).toContain('mode=manual');
    expect(url).toContain('datetime=2026-03-22T06%3A32%3A00');
    expect(url).toContain('location=Israel');
    expect(url).toContain('timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
    expect(url).toContain('house_system_code=R');
    expect(url).toContain('case_type=child');
    expect(url).toContain('abduction=1');
    expect(url).toContain('origin=31.7683%2C35.2137');
    expect(url).toContain('line_zones=1');
    expect(url).toContain('corridor_deg=7');
  });

  it('uses an extended timeout for synastry requests', async () => {
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getSynastry({
      snapAId: 'snap-a',
      snapBId: 'snap-b',
      engineId: 'union_dynamics',
      profileA: 'feminine',
      profileB: 'masculine',
      includeModern: true,
    });

    expect(String(fetch.mock.calls[0][0])).toContain('/api/astro-clock/synastry?');
    expect(String(fetch.mock.calls[0][0])).toContain('snap_a_id=snap-a');
    expect(String(fetch.mock.calls[0][0])).toContain('snap_b_id=snap-b');
    expect(String(fetch.mock.calls[0][0])).toContain('engine_id=union_dynamics');
    expect(String(fetch.mock.calls[0][0])).toContain('profile_a=feminine');
    expect(String(fetch.mock.calls[0][0])).toContain('profile_b=masculine');
    expect(String(fetch.mock.calls[0][0])).toContain('include_modern=1');
    expect(String(fetch.mock.calls[0][0])).not.toContain('house_system_code=');
    expect(setTimeoutSpy.mock.calls.some(([, timeout]) => timeout === 300000)).toBe(true);
  });

  it('serializes astrocartography inspect requests with the selected filters', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));
    await AstroClockAPI.getAstrocartographyLocation({
      natalSnapId: 'snap-1',
      houseSystem: 'R',
      goalId: 'sex',
      targetLocation: 'Ciego de Avila, Cuba',
      bodies: ['Moon'],
      angles: ['IC'],
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/astrocartography/location?');
    expect(url).toContain('natal_snap_id=snap-1');
    expect(url).toContain('house_system_code=R');
    expect(url).toContain('goal_id=sex');
    expect(url).toContain('target_location=Ciego+de+Avila%2C+Cuba');
    expect(url).not.toContain('target_latitude=');
    expect(url).not.toContain('target_longitude=');
    expect(url).not.toContain('target_label=');
    expect(url).not.toContain('target_timezone=');
    expect(url).toContain('body=Moon');
    expect(url).toContain('angle=IC');
  });

  it('serializes astrocartography manual natal coordinates', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.getAstrocartographyMap({
      natalDatetime: '2026-03-22T04:32:00Z',
      natalLocation: 'Jerusalem',
      natalTimezone: 'Asia/Jerusalem',
      latitude: 31.778,
      longitude: 35.235,
      houseSystem: 'R',
    });

    const url = String(fetch.mock.calls[0][0]);
    expect(url).toContain('/api/astro-clock/astrocartography/map?');
    expect(url).toContain('natal_datetime=2026-03-22T04%3A32%3A00Z');
    expect(url).toContain('natal_location=Jerusalem');
    expect(url).toContain('natal_timezone=Asia%2FJerusalem');
    expect(url).toContain('latitude=31.778');
    expect(url).toContain('longitude=35.235');
  });

  it('serializes astrocartography atlas cancel requests with the session id', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: {} }));

    await AstroClockAPI.cancelAstrocartographyAtlasSearch('session-42');

    expect(String(fetch.mock.calls[0][0])).toContain('/api/astro-clock/astrocartography/atlas-search/cancel');
    expect(fetch.mock.calls[0][1].method).toBe('POST');
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ session_id: 'session-42' });
  });

  it('loads the research evaluator catalog', async () => {
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { families: [] } }));

    await AstroClockAPI.listResearchEvaluators();

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/research/evaluators');
  });

  it('posts research analysis requests to the chart-set endpoint with an extended timeout', async () => {
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');
    fetch.mockResolvedValueOnce(makeJsonResponse(200, { success: true, data: { signals: [] } }));

    await AstroClockAPI.runResearchAnalysis({
      charts: [{ name: 'Subject A', date: '1990-01-13', time: '21:33', location: 'Jerusalem, Israel' }],
      evaluator_families: ['positions', 'points'],
      control: { strategy: 'matched_generated', per_chart: 2 },
    });

    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:52525/api/astro-clock/research/analyze');
    expect(fetch.mock.calls[0][1].method).toBe('POST');
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(expect.objectContaining({
      evaluator_families: ['positions', 'points'],
      control: expect.objectContaining({ strategy: 'matched_generated', per_chart: 2 }),
    }));
    expect(setTimeoutSpy.mock.calls.some(([, timeout]) => timeout === 300000)).toBe(true);
  });
});
