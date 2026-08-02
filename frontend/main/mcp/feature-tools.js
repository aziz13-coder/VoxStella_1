const z = require('zod/v4');


const HOUSE_SYSTEM_CODES = ['R', 'P', 'E', 'W', 'O', 'C', 'K', 'T'];
const ASTRO_BODIES = [
  'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
  'North Node', 'Uranus', 'Neptune', 'Pluto', 'Chiron',
];
const ASTRO_ANGLES = ['ASC', 'DSC', 'MC', 'IC'];
const ISO_DATETIME = z.string().min(16).max(80)
  .regex(/^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}/)
  .describe('ISO-8601 date and time, including an offset when the local time may be ambiguous');
const LATITUDE = z.number().min(-90).max(90);
const LONGITUDE = z.number().min(-180).max(180);
const TIMEZONE = z.string().min(1).max(100).describe('IANA timezone name');
const LOCATION = z.string().min(1).max(200);
const MCP_FEATURE_SCHEMA_VERSION = 'voxstella.features.v1';
const READ_ONLY_ANNOTATIONS = Object.freeze({
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
});

const MCP_FEATURE_TOOL_NAMES = Object.freeze([
  'analyze_synastry',
  'calculate_trait_profile',
  'analyze_transits',
  'scan_transit_window',
  'analyze_astrocartography_location',
  'generate_astrocartography_map',
  'compare_astrocartography_locations',
  'search_astrocartography_atlas',
  'find_election_times',
  'calculate_bazi',
  'analyze_chinese_compatibility',
  'cast_iching_oracle',
  'analyze_forensic_event',
  'run_birth_time_certification',
]);

const EXPLICIT_CHART_SCHEMA = z.object({
  label: z.string().min(1).max(200).optional(),
  datetime: ISO_DATETIME,
  latitude: LATITUDE,
  longitude: LONGITUDE,
  timezone: TIMEZONE,
  location: LOCATION.optional(),
  house_system_code: z.enum(HOUSE_SYSTEM_CODES).default('R'),
});

const EXPLICIT_CLOCK_SCHEMA = z.object({
  datetime: ISO_DATETIME,
  latitude: LATITUDE,
  longitude: LONGITUDE,
  timezone: TIMEZONE,
  location: LOCATION,
  house_system_code: z.enum(HOUSE_SYSTEM_CODES).default('R'),
});

const NATAL_FIELDS = {
  natal_datetime: ISO_DATETIME,
  natal_location: LOCATION,
  natal_timezone: TIMEZONE,
  latitude: LATITUDE,
  longitude: LONGITUDE,
  house_system_code: z.enum(HOUSE_SYSTEM_CODES).default('R'),
};

const TRANSIT_OPTIONS = {
  detail_level: z.enum(['summary', 'full']).default('summary'),
  include_modern: z.boolean().default(false),
  include_natal_modern: z.boolean().default(false),
  include_cusps: z.boolean().default(false),
  include_antiscia: z.boolean().default(false),
  include_lots: z.boolean().default(false),
  focus_houses: z.array(z.number().int().min(1).max(12)).max(12).optional(),
  focus_planets: z.array(z.enum(ASTRO_BODIES)).max(ASTRO_BODIES.length).optional(),
  sensitive_houses: z.array(z.number().int().min(1).max(12)).max(12).optional(),
  sensitive_planets: z.array(z.enum(ASTRO_BODIES)).max(ASTRO_BODIES.length).optional(),
  transiting_bodies: z.array(z.enum(ASTRO_BODIES)).max(ASTRO_BODIES.length).optional(),
  natal_bodies: z.array(z.enum(ASTRO_BODIES)).max(ASTRO_BODIES.length).optional(),
  aspects: z.array(z.string().min(1).max(40)).max(16).optional(),
};

const ASTROCARTOGRAPHY_NATAL_FIELDS = {
  ...NATAL_FIELDS,
  transit_datetime: ISO_DATETIME.optional(),
  transit_location: LOCATION.optional(),
  transit_timezone: TIMEZONE.optional(),
  bodies: z.array(z.enum(ASTRO_BODIES)).min(1).max(ASTRO_BODIES.length).optional(),
  angles: z.array(z.enum(ASTRO_ANGLES)).min(1).max(ASTRO_ANGLES.length).optional(),
};

const CHINESE_BIRTH_SCHEMA = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  time: z.string().regex(/^\d{2}:\d{2}(?::\d{2})?$/).optional(),
  location: LOCATION,
  timezone: TIMEZONE,
  latitude: LATITUDE,
  longitude: LONGITUDE,
});

const CERTIFICATION_EVENT_SCHEMA = z.object({
  label: z.string().min(1).max(200),
  timestamp: ISO_DATETIME,
  latitude: LATITUDE,
  longitude: LONGITUDE,
  timezone: TIMEZONE.optional(),
  precision: z.number().int().min(0).max(12).default(1),
  theme: z.string().min(1).max(200).optional(),
  weight: z.number().positive().max(100).default(1),
  source_note: z.string().max(500).optional(),
});

function resultContent(data) {
  return {
    content: [{ type: 'text', text: JSON.stringify(data, null, 2) }],
    structuredContent: data,
  };
}

function queryFrom(args, {
  aliases = {},
  arrays = [],
  booleans = [],
  omit = [],
} = {}) {
  const out = {};
  const arrayFields = new Set(arrays);
  const booleanFields = new Set(booleans);
  const omitted = new Set(omit);
  for (const [sourceKey, value] of Object.entries(args || {})) {
    if (omitted.has(sourceKey) || value === undefined || value === null || value === '') continue;
    const targetKey = aliases[sourceKey] || sourceKey;
    if (arrayFields.has(sourceKey)) {
      if (Array.isArray(value) && value.length) out[targetKey] = value;
    } else if (booleanFields.has(sourceKey)) {
      out[targetKey] = value ? '1' : '0';
    } else {
      out[targetKey] = value;
    }
  }
  return out;
}

function transitQuery(args) {
  const query = queryFrom(args, {
    aliases: {
      focus_houses: 'focus_house',
      focus_planets: 'focus_planet',
      sensitive_houses: 'sensitive_house',
      sensitive_planets: 'sensitive_planet',
      transiting_bodies: 'transiting',
      natal_bodies: 'natal',
      aspects: 'aspect',
    },
    arrays: [
      'focus_houses', 'focus_planets', 'sensitive_houses', 'sensitive_planets',
      'transiting_bodies', 'natal_bodies', 'aspects',
    ],
    booleans: [
      'include_modern', 'include_natal_modern', 'include_cusps',
      'include_antiscia', 'include_lots', 'sig_beta',
    ],
    omit: ['detail_level'],
  });
  query.response_detail = args?.detail_level === 'full' ? 'full' : 'compact';
  return query;
}

function astrocartographyQuery(args, extra = {}) {
  return queryFrom(args, {
    aliases: { bodies: 'body', angles: 'angle', ...(extra.aliases || {}) },
    arrays: ['bodies', 'angles', ...(extra.arrays || [])],
    omit: extra.omit || [],
  });
}

function electionQuery(args) {
  return queryFrom(args, {
    aliases: {
      weekdays: 'weekday',
      participant_snap_ids: 'participant_snap_id',
      marriage_beta_selected_line_ids: 'marriage_beta_selected_line_id',
      business_beta_selected_line_ids: 'business_beta_selected_line_id',
      estate_selected_line_ids: 'estate_selected_line_id',
    },
    arrays: [
      'weekdays', 'participant_snap_ids', 'marriage_beta_selected_line_ids',
      'business_beta_selected_line_ids', 'estate_selected_line_ids',
    ],
    booleans: [
      'reference_parity', 'include_series', 'include_sr_lr', 'include_lunation_screen',
      'include_fixed_stars', 'include_traditional_timing', 'emphasize_commerce',
      'prefer_fixed_asc', 'saturn_binding_ok',
    ],
  });
}

function registerReadOnlyTool(server, name, definition, handler, { idempotent = true } = {}) {
  server.registerTool(name, {
    ...definition,
    outputSchema: z.looseObject({
      mcp_schema_version: z.literal(MCP_FEATURE_SCHEMA_VERSION),
      feature_tool: z.literal(name),
    }),
    annotations: { ...READ_ONLY_ANNOTATIONS, idempotentHint: idempotent },
  }, async (args, ctx) => {
    const data = await handler(args, ctx);
    return resultContent({
      ...(data && typeof data === 'object' && !Array.isArray(data) ? data : { result: data }),
      mcp_schema_version: MCP_FEATURE_SCHEMA_VERSION,
      feature_tool: name,
    });
  });
}

function registerLicensedFeatureTools(server, licensedBackendCall) {
  registerReadOnlyTool(server, 'analyze_synastry', {
    title: 'Analyze synastry',
    description: 'Compare two explicit charts with Vox Stella Synastry without reading or creating saved charts.',
    inputSchema: z.object({
      chart_a: EXPLICIT_CHART_SCHEMA,
      chart_b: EXPLICIT_CHART_SCHEMA,
      engine_id: z.enum(['memo', 'life_themes', 'union_dynamics', 'work_alliance']).default('memo'),
      profile_a: z.enum(['blended', 'feminine', 'masculine']).default('blended'),
      profile_b: z.enum(['blended', 'feminine', 'masculine']).default('blended'),
      include_modern: z.boolean().default(true),
      include_nodes: z.boolean().default(true),
      include_chiron: z.boolean().default(false),
      orb_profile: z.enum(['tight', 'balanced', 'wide']).default('balanced'),
    }),
  }, (args, ctx) => licensedBackendCall('/api/mcp/synastry', args, {
    signal: ctx.mcpReq.signal,
    timeoutMs: 300000,
  }));

  registerReadOnlyTool(server, 'calculate_trait_profile', {
    title: 'Calculate Trait Profile',
    description: 'Calculate the complete Vox Stella Trait Profile for an explicit natal chart.',
    inputSchema: z.object({
      ...EXPLICIT_CLOCK_SCHEMA.shape,
      special_degrees: z.array(z.string().min(1).max(40)).max(32).optional(),
      summary_context: z.enum(['default', 'public_figure_biography']).default('default'),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/traits/profile', undefined, {
    method: 'GET',
    query: queryFrom(args, {
      aliases: { special_degrees: 'special_degree' },
      arrays: ['special_degrees'],
    }),
    signal: ctx.mcpReq.signal,
    timeoutMs: 120000,
  }));

  registerReadOnlyTool(server, 'analyze_transits', {
    title: 'Analyze exact transits',
    description: 'Analyze transits to an explicit natal chart at one exact timestamp.',
    inputSchema: z.object({
      ...NATAL_FIELDS,
      transit_datetime: ISO_DATETIME,
      ...TRANSIT_OPTIONS,
      sig_beta: z.boolean().optional(),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/transits', undefined, {
    method: 'GET', query: transitQuery(args), signal: ctx.mcpReq.signal, timeoutMs: 180000,
  }));

  registerReadOnlyTool(server, 'scan_transit_window', {
    title: 'Scan transit window',
    description: 'Scan a bounded time window for transit peaks and predictions against an explicit natal chart.',
    inputSchema: z.object({
      ...NATAL_FIELDS,
      start: ISO_DATETIME,
      end: ISO_DATETIME,
      step_minutes: z.number().int().min(1).max(1440).default(60),
      ...TRANSIT_OPTIONS,
      sig_beta: z.boolean().optional(),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/transits/window', undefined, {
    method: 'GET', query: transitQuery(args), signal: ctx.mcpReq.signal, timeoutMs: 300000,
  }));

  registerReadOnlyTool(server, 'analyze_astrocartography_location', {
    title: 'Analyze astrocartography location',
    description: 'Evaluate one exact target location against an explicit natal chart and optional goal.',
    inputSchema: z.object({
      ...ASTROCARTOGRAPHY_NATAL_FIELDS,
      target_location: LOCATION,
      target_latitude: LATITUDE,
      target_longitude: LONGITUDE,
      target_id: z.string().min(1).max(200).optional(),
      goal_id: z.string().min(1).max(100).optional(),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/astrocartography/location', undefined, {
    method: 'GET', query: astrocartographyQuery(args), signal: ctx.mcpReq.signal, timeoutMs: 180000,
  }));

  registerReadOnlyTool(server, 'generate_astrocartography_map', {
    title: 'Generate astrocartography map data',
    description: 'Generate global astrocartography line data for an explicit natal chart.',
    inputSchema: z.object(ASTROCARTOGRAPHY_NATAL_FIELDS),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/astrocartography/map', undefined, {
    method: 'GET', query: astrocartographyQuery(args), signal: ctx.mcpReq.signal, timeoutMs: 180000,
  }));

  registerReadOnlyTool(server, 'compare_astrocartography_locations', {
    title: 'Compare astrocartography locations',
    description: 'Compare two to ten exact target locations for one explicit natal chart.',
    inputSchema: z.object({
      ...ASTROCARTOGRAPHY_NATAL_FIELDS,
      goal_id: z.string().min(1).max(100).optional(),
      targets: z.array(z.object({
        location: LOCATION,
        latitude: LATITUDE,
        longitude: LONGITUDE,
        target_id: z.string().min(1).max(200).optional(),
      })).min(2).max(10),
    }),
  }, (args, ctx) => {
    const query = astrocartographyQuery(args, { omit: ['targets'] });
    query.target_location = args.targets.map((target) => target.location);
    query.target_latitude = args.targets.map((target) => target.latitude);
    query.target_longitude = args.targets.map((target) => target.longitude);
    if (args.targets.every((target) => target.target_id)) {
      query.target_id = args.targets.map((target) => target.target_id);
    }
    return licensedBackendCall('/api/astro-clock/astrocartography/compare', undefined, {
      method: 'GET', query, signal: ctx.mcpReq.signal, timeoutMs: 180000,
    });
  });

  registerReadOnlyTool(server, 'search_astrocartography_atlas', {
    title: 'Search astrocartography atlas',
    description: 'Rank bounded atlas candidates for an explicit natal chart and required Astrocartography goal.',
    inputSchema: z.object({
      ...ASTROCARTOGRAPHY_NATAL_FIELDS,
      goal_id: z.string().min(1).max(100)
        .describe('Canonical Vox Stella goal ID, for example love, career, home, education, or travel_relax'),
      query: z.string().max(200).optional(),
      country_code: z.string().length(2).optional(),
      continent_code: z.string().min(2).max(3).optional(),
      resolution: z.enum(['coarse', 'standard', 'fine', 'ultra']).default('standard'),
      limit: z.number().int().min(1).max(20).default(20),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/astrocartography/atlas-search', undefined, {
    method: 'GET', query: astrocartographyQuery(args), signal: ctx.mcpReq.signal, timeoutMs: 300000,
  }));

  registerReadOnlyTool(server, 'find_election_times', {
    title: 'Find election times',
    description: 'Run a bounded Vox Stella Election scan and return the top candidate times.',
    inputSchema: z.object({
      matter: z.enum(['marriage', 'surgery', 'business', 'estate', 'contract', 'journey', 'haircut', 'beautification', 'conception', 'lunar_fertility', 'viral', 'battle', 'legal']),
      start: ISO_DATETIME,
      end: ISO_DATETIME,
      location: LOCATION,
      timezone: TIMEZONE,
      latitude: LATITUDE,
      longitude: LONGITUDE,
      house_system_code: z.enum(HOUSE_SYSTEM_CODES).default('R'),
      step_minutes: z.number().int().min(1).max(1440).default(60),
      limit: z.number().int().min(1).max(50).default(15),
      include_series: z.boolean().default(false),
      reference_parity: z.boolean().default(false),
      include_sr_lr: z.boolean().default(false),
      weekday_mode: z.enum(['all', 'custom', 'none']).optional(),
      weekdays: z.array(z.enum(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'])).max(7).optional(),
      hour_start: z.number().min(0).max(24).optional(),
      hour_end: z.number().min(0).max(24).optional(),
      marriage_algorithm: z.enum(['alpha', 'beta']).optional(),
      business_algorithm: z.enum(['alpha', 'beta']).optional(),
      estate_direction: z.enum(['buy', 'sell']).optional(),
      participant_a_snap_id: z.string().min(1).max(200).optional(),
      participant_b_snap_id: z.string().min(1).max(200).optional(),
      participant_snap_ids: z.array(z.string().min(1).max(200)).max(16).optional(),
      estate_participant_snap_id: z.string().min(1).max(200).optional(),
      natal_snap_id: z.string().min(1).max(200).optional(),
      natal_datetime: ISO_DATETIME.optional(),
      natal_location: LOCATION.optional(),
      natal_timezone: TIMEZONE.optional(),
      gender: z.enum(['male', 'female']).optional(),
      hair_goal: z.string().min(1).max(100).optional(),
      surgery_sign: z.string().min(1).max(40).optional(),
      procedure: z.string().min(1).max(100).optional(),
      business_mode: z.string().min(1).max(100).optional(),
      journey_type: z.string().min(1).max(100).optional(),
      legal_action: z.string().min(1).max(100).optional(),
      action_type: z.string().min(1).max(100).optional(),
      body_parts: z.string().min(1).max(300).optional(),
      body_signs: z.string().min(1).max(300).optional(),
      procedure_type: z.string().min(1).max(100).optional(),
      contract_mode: z.string().min(1).max(100).optional(),
      include_lunation_screen: z.boolean().default(false),
      include_fixed_stars: z.boolean().default(false),
      include_traditional_timing: z.boolean().default(false),
      emphasize_commerce: z.boolean().default(false),
      prefer_fixed_asc: z.boolean().optional(),
      saturn_binding_ok: z.boolean().optional(),
      min_mercury_direct_days: z.number().int().min(0).max(365).optional(),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/election/suggest/stream', undefined, {
    method: 'GET',
    query: electionQuery(args),
    responseType: 'sse',
    signal: ctx.mcpReq.signal,
    timeoutMs: 300000,
  }));

  registerReadOnlyTool(server, 'calculate_bazi', {
    title: 'Calculate BaZi',
    description: 'Calculate a Four Pillars BaZi profile from explicit birth data.',
    inputSchema: z.object({
      birth: CHINESE_BIRTH_SCHEMA,
      calculation_sex: z.enum(['male', 'female']).optional(),
      include_luck_pillars: z.boolean().default(false),
      use_true_solar_time: z.boolean().default(false),
      day_boundary_rule: z.enum(['civil_midnight', 'true_solar_midnight']).default('civil_midnight'),
      hour_pillar_variant: z.enum(['standard_zi_hour', 'late_zi_next_day']).default('standard_zi_hour'),
      luck_direction_rule: z.enum(['year_stem_polarity', 'day_stem_polarity']).default('year_stem_polarity'),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/chinese-astrology/bazi', args, {
    signal: ctx.mcpReq.signal, timeoutMs: 120000,
  }));

  registerReadOnlyTool(server, 'analyze_chinese_compatibility', {
    title: 'Analyze Chinese Astrology compatibility',
    description: 'Compare two explicit BaZi birth profiles without reading saved charts.',
    inputSchema: z.object({
      primary: CHINESE_BIRTH_SCHEMA,
      relationship: CHINESE_BIRTH_SCHEMA,
      relationship_context: z.enum(['general', 'romantic', 'family', 'business']).default('general'),
      primary_calculation_sex: z.enum(['male', 'female']).optional(),
      relationship_calculation_sex: z.enum(['male', 'female']).optional(),
      include_luck_pillars: z.boolean().default(true),
      use_true_solar_time: z.boolean().default(false),
      day_boundary_rule: z.enum(['civil_midnight', 'true_solar_midnight']).default('civil_midnight'),
      hour_pillar_variant: z.enum(['standard_zi_hour', 'late_zi_next_day']).default('standard_zi_hour'),
      luck_direction_rule: z.enum(['year_stem_polarity', 'day_stem_polarity']).default('year_stem_polarity'),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/chinese-astrology/compatibility', args, {
    signal: ctx.mcpReq.signal, timeoutMs: 180000,
  }));

  registerReadOnlyTool(server, 'cast_iching_oracle', {
    title: 'Cast I Ching oracle',
    description: 'Cast a read-only I Ching result using coins, yarrow probabilities, or six explicit manual lines.',
    inputSchema: z.object({
      question: z.string().max(1000).default(''),
      method: z.enum(['coins', 'yarrow', 'manual']).default('coins'),
      lines: z.array(z.number().int().min(6).max(9)).length(6).optional(),
      seed: z.union([z.string().max(200), z.number().int()]).optional(),
      coin_value_scheme: z.enum(['heads_2_tails_3', 'heads_3_tails_2']).default('heads_2_tails_3'),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/chinese-astrology/iching-oracle', args, {
    signal: ctx.mcpReq.signal, timeoutMs: 120000,
  }), { idempotent: false });

  registerReadOnlyTool(server, 'analyze_forensic_event', {
    title: 'Analyze forensic event',
    description: 'Run the AstroClock forensic rule engine for an explicit event chart. Results are symbolic astrology, not factual evidence or suspect identification.',
    inputSchema: z.object({
      ...EXPLICIT_CLOCK_SCHEMA.shape,
      case_type: z.enum(['general', 'child', 'adult_female']).default('general'),
      abduction: z.boolean().default(false),
      origin_latitude: LATITUDE.optional(),
      origin_longitude: LONGITUDE.optional(),
      line_zones: z.boolean().default(false),
      corridor_deg: z.number().min(0.1).max(45).optional(),
    }).superRefine((value, ctx) => {
      if ((value.origin_latitude === undefined) !== (value.origin_longitude === undefined)) {
        ctx.addIssue({ code: 'custom', message: 'origin_latitude and origin_longitude must be supplied together' });
      }
    }),
  }, (args, ctx) => {
    const query = queryFrom(args, {
      booleans: ['abduction', 'line_zones'],
      omit: ['origin_latitude', 'origin_longitude'],
    });
    if (args.origin_latitude !== undefined && args.origin_longitude !== undefined) {
      query.origin = `${args.origin_latitude},${args.origin_longitude}`;
    }
    return licensedBackendCall('/api/astro-clock/forensic', undefined, {
      method: 'GET', query, signal: ctx.mcpReq.signal, timeoutMs: 180000,
    });
  });

  registerReadOnlyTool(server, 'run_birth_time_certification', {
    title: 'Run birth-time certification',
    description: 'Run Vox Stella birth-time rectification and return its evidence-quality certification assessment.',
    inputSchema: z.object({
      birth: z.object({
        date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
        location: LOCATION,
        timezone: TIMEZONE,
        latitude: LATITUDE,
        longitude: LONGITUDE,
        source_time_status: z.string().min(1).max(100).optional(),
      }),
      search: z.object({
        start_time: z.string().regex(/^\d{2}:\d{2}$/),
        end_time: z.string().regex(/^\d{2}:\d{2}$/),
      }),
      events: z.array(CERTIFICATION_EVENT_SCHEMA).min(1).max(100),
      house_system_code: z.enum(HOUSE_SYSTEM_CODES).default('T'),
      orb_degrees: z.number().min(0.1).max(10).default(1),
      level_percent: z.number().int().min(1).max(100).default(67),
      include_series: z.boolean().default(false),
      max_rows: z.number().int().min(1).max(1441).default(1441),
      instruments: z.array(z.union([z.string().min(1).max(100), z.looseObject({})])).max(32).optional(),
      object_weights: z.record(z.string(), z.number()).optional(),
      aspect_weights: z.record(z.string(), z.number()).optional(),
    }),
  }, (args, ctx) => licensedBackendCall('/api/astro-clock/certification/rectify', args, {
    signal: ctx.mcpReq.signal, timeoutMs: 300000,
  }));
}


module.exports = {
  MCP_FEATURE_SCHEMA_VERSION,
  MCP_FEATURE_TOOL_NAMES,
  registerLicensedFeatureTools,
};
