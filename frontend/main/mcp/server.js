const { McpServer } = require('@modelcontextprotocol/server');
const { serveStdio } = require('@modelcontextprotocol/server/stdio');
const z = require('zod/v4');

const {
  assertLicensedMcpAccess,
  createLicensedBackendClient,
} = require('./licensed-backend-client');

const HOUSE_SYSTEM_CODES = ['R', 'P', 'E', 'W', 'O', 'C', 'K', 'T'];
const BODIES = [
  'Sun',
  'Moon',
  'Mercury',
  'Venus',
  'Mars',
  'Jupiter',
  'Saturn',
  'North Node',
  'Uranus',
  'Neptune',
  'Pluto',
  'Chiron',
];
const SECTIONS = [
  'metadata',
  'angles',
  'planets',
  'houses',
  'aspects',
  'moon',
  'considerations',
];

const LOCATION_INPUT = {
  latitude: z.number().min(-90).max(90).describe('Geographic latitude in decimal degrees'),
  longitude: z.number().min(-180).max(180).describe('Geographic longitude in decimal degrees; east is positive'),
  timezone: z.string().min(1).max(100).describe('IANA timezone name, for example America/Los_Angeles'),
  location: z.string().min(1).max(200).optional().describe('Human-readable location label; coordinates remain authoritative'),
};

const CHART_OPTIONS = {
  house_system_code: z.enum(HOUSE_SYSTEM_CODES).default('R').describe('House system code; R is Regiomontanus'),
  bodies: z.array(z.enum(BODIES)).min(1).max(BODIES.length).optional().describe('Bodies to return; defaults to classical planets plus North Node'),
  sections: z.array(z.enum(SECTIONS)).min(1).max(SECTIONS.length).optional().describe('Response sections to return'),
  include_modern: z.boolean().optional().describe('Include Uranus, Neptune, and Pluto in the result'),
  include_chiron: z.boolean().optional().describe('Include Chiron in the result'),
};

const CALCULATION_CONTEXT_SCHEMA = z.looseObject({
  timestamp: z.string(),
  location: z.string(),
  timezone: z.string(),
  latitude: z.number(),
  longitude: z.number(),
});
const CAPABILITIES_OUTPUT_SCHEMA = z.looseObject({
  schema_version: z.string(),
  app_version: z.string(),
  license_required: z.literal(true),
  tools: z.array(z.string()),
  house_systems: z.array(z.looseObject({ code: z.string(), name: z.string() })),
  bodies: z.looseObject({
    default: z.array(z.string()),
    optional: z.array(z.string()),
  }),
  sections: z.array(z.string()),
});
const CHART_OUTPUT_SCHEMA = z.looseObject({
  schema_version: z.string(),
  calculation: CALCULATION_CONTEXT_SCHEMA,
  angles: z.looseObject({}).optional(),
  planets: z.array(z.looseObject({ body: z.string(), longitude: z.number().nullable() })).optional(),
  houses: z.array(z.looseObject({ house: z.number(), cusp_longitude: z.number().nullable() })).optional(),
  aspects: z.array(z.looseObject({ body1: z.string(), body2: z.string(), aspect: z.string().nullable() })).optional(),
  moon: z.looseObject({}).optional(),
  considerations: z.looseObject({}).optional(),
});
const PLANETARY_HOURS_OUTPUT_SCHEMA = z.looseObject({
  schema_version: z.string(),
  calculation: CALCULATION_CONTEXT_SCHEMA,
  day_ruler: z.string(),
  sunrise: z.string(),
  sunset: z.string(),
  hours: z.array(z.looseObject({
    hour_number: z.number(),
    ruling_planet: z.string(),
    start_time: z.string(),
    end_time: z.string(),
  })).length(24),
  current_hour: z.looseObject({}).nullable(),
});

function resultContent(data) {
  return {
    content: [{ type: 'text', text: JSON.stringify(data, null, 2) }],
    structuredContent: data,
  };
}

function resourceContent(uri, data) {
  return {
    contents: [{
      uri,
      mimeType: 'application/json',
      text: JSON.stringify(data, null, 2),
    }],
  };
}

function createVoxStellaMcpServer({ appVersion, licensedBackendCall }) {
  if (typeof licensedBackendCall !== 'function') {
    throw new TypeError('licensedBackendCall is required');
  }
  const version = String(appVersion || 'development');
  const server = new McpServer({
    name: 'vox-stella',
    title: 'Vox Stella Astrology Engine',
    version,
  });

  server.registerTool('get_astrological_capabilities', {
    title: 'Get astrological capabilities',
    description: 'List the licensed Vox Stella MCP schema, supported house systems, bodies, sections, and required parameters.',
    outputSchema: CAPABILITIES_OUTPUT_SCHEMA,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  }, async () => resultContent(await licensedBackendCall('/api/mcp/capabilities', undefined, { method: 'GET' })));

  server.registerTool('calculate_astrological_chart', {
    title: 'Calculate astrological chart',
    description: 'Calculate a deterministic chart for an explicit ISO-8601 date/time, coordinates, IANA timezone, house system, and selected output sections.',
    inputSchema: z.object({
      datetime: z.string().min(1).max(80).describe('ISO-8601 date and time; a naive civil time is interpreted in timezone'),
      ...LOCATION_INPUT,
      ...CHART_OPTIONS,
    }),
    outputSchema: CHART_OUTPUT_SCHEMA,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  }, async (args) => resultContent(await licensedBackendCall('/api/mcp/chart', args)));

  server.registerTool('get_current_astrological_positions', {
    title: 'Get current astrological positions',
    description: 'Calculate positions for the current instant at explicit coordinates and an IANA timezone.',
    inputSchema: z.object({
      ...LOCATION_INPUT,
      ...CHART_OPTIONS,
    }),
    outputSchema: CHART_OUTPUT_SCHEMA,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: false,
    },
  }, async (args) => resultContent(await licensedBackendCall('/api/mcp/current-positions', args)));

  server.registerTool('calculate_planetary_hours', {
    title: 'Calculate planetary hours',
    description: 'Calculate the 24 unequal traditional planetary hours for the local date containing the supplied ISO-8601 time, or for now when datetime is omitted.',
    inputSchema: z.object({
      datetime: z.string().min(1).max(80).optional().describe('Optional ISO-8601 time selecting the local date and current hour'),
      ...LOCATION_INPUT,
    }),
    outputSchema: PLANETARY_HOURS_OUTPUT_SCHEMA,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: false,
    },
  }, async (args) => resultContent(await licensedBackendCall('/api/mcp/planetary-hours', args)));

  server.registerResource(
    'astrological-capabilities',
    'voxstella://capabilities',
    {
      title: 'Vox Stella astrological capabilities',
      description: 'Versioned calculation parameters supported by this licensed installation.',
      mimeType: 'application/json',
    },
    async () => resourceContent(
      'voxstella://capabilities',
      await licensedBackendCall('/api/mcp/capabilities', undefined, { method: 'GET' }),
    ),
  );

  server.registerResource(
    'engine-version',
    'voxstella://engine/version',
    {
      title: 'Vox Stella engine version',
      description: 'Installed MCP server and calculation schema version.',
      mimeType: 'application/json',
    },
    async () => {
      const capabilities = await licensedBackendCall('/api/mcp/capabilities', undefined, { method: 'GET' });
      return resourceContent('voxstella://engine/version', {
        app_version: capabilities.app_version || version,
        schema_version: capabilities.schema_version,
        license_required: true,
      });
    },
  );

  return server;
}

async function startLicensedMcpServer({
  apiBaseUrl,
  appVersion,
  licenseManager,
  transport,
}) {
  // Fail closed before constructing or advertising an MCP server.  A copied
  // client config therefore has no value on an unlicensed installation.
  await assertLicensedMcpAccess(licenseManager);
  const licensedBackendCall = createLicensedBackendClient({ apiBaseUrl, licenseManager });
  return serveStdio(
    () => createVoxStellaMcpServer({ appVersion, licensedBackendCall }),
    {
      ...(transport ? { transport } : {}),
      legacy: 'serve',
    },
  );
}

module.exports = {
  BODIES,
  HOUSE_SYSTEM_CODES,
  SECTIONS,
  createVoxStellaMcpServer,
  startLicensedMcpServer,
};
