const { requestJson, requestText } = require('../backend-http');

const DEFAULT_TIMEOUT_MS = 30000;
const DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024;
const MAX_FEATURE_TIMEOUT_MS = 5 * 60 * 1000;
const MAX_REQUEST_URL_LENGTH = 64 * 1024;

const MCP_CALCULATION_ROUTE_RULES = Object.freeze({
  '/api/mcp/capabilities': { methods: ['GET'], query: [] },
  '/api/mcp/chart': { methods: ['POST'], query: [] },
  '/api/mcp/current-positions': { methods: ['POST'], query: [] },
  '/api/mcp/planetary-hours': { methods: ['POST'], query: [] },
  '/api/mcp/synastry': { methods: ['POST'], query: [] },
});

const FEATURE_ROUTE_RULES = Object.freeze({
  '/api/astro-clock/traits/profile': {
    methods: ['GET'],
    query: ['snap_id', 'mode', 'datetime', 'location', 'timezone', 'latitude', 'longitude', 'house_system_code', 'special_degree', 'summary_context'],
  },
  '/api/astro-clock/transits': {
    methods: ['GET'],
    query: ['natal_snap_id', 'natal_datetime', 'natal_location', 'natal_timezone', 'house_system_code', 'latitude', 'longitude', 'transit_datetime', 'include_modern', 'include_natal_modern', 'include_cusps', 'include_antiscia', 'include_lots', 'focus_house', 'focus_planet', 'sensitive_house', 'sensitive_planet', 'transiting', 'natal', 'aspect', 'pd_start', 'pd_end', 'prog_start', 'prog_end', 'sa_start', 'sa_end', 'sig_beta'],
  },
  '/api/astro-clock/transits/window': {
    methods: ['GET'],
    query: ['natal_snap_id', 'natal_datetime', 'natal_location', 'natal_timezone', 'house_system_code', 'latitude', 'longitude', 'start', 'end', 'center', 'range_hours', 'step_minutes', 'include_modern', 'include_natal_modern', 'include_cusps', 'include_antiscia', 'include_lots', 'focus_house', 'focus_planet', 'sensitive_house', 'sensitive_planet', 'transiting', 'natal', 'aspect', 'pd_start', 'pd_end', 'prog_start', 'prog_end', 'sa_start', 'sa_end', 'sig_beta'],
  },
  '/api/astro-clock/astrocartography/location': {
    methods: ['GET'],
    query: ['natal_snap_id', 'natal_datetime', 'natal_location', 'natal_timezone', 'house_system_code', 'latitude', 'longitude', 'goal_id', 'transit_datetime', 'transit_location', 'transit_timezone', 'target_location', 'target_id', 'target_latitude', 'target_longitude', 'body', 'angle'],
  },
  '/api/astro-clock/astrocartography/map': {
    methods: ['GET'],
    query: ['natal_snap_id', 'natal_datetime', 'natal_location', 'natal_timezone', 'house_system_code', 'latitude', 'longitude', 'transit_datetime', 'transit_location', 'transit_timezone', 'body', 'angle'],
  },
  '/api/astro-clock/astrocartography/compare': {
    methods: ['GET'],
    query: ['natal_snap_id', 'natal_datetime', 'natal_location', 'natal_timezone', 'house_system_code', 'latitude', 'longitude', 'goal_id', 'transit_datetime', 'transit_location', 'transit_timezone', 'target_location', 'target_id', 'target_latitude', 'target_longitude', 'body', 'angle'],
  },
  '/api/astro-clock/astrocartography/atlas-search': {
    methods: ['GET'],
    query: ['natal_snap_id', 'natal_datetime', 'natal_location', 'natal_timezone', 'house_system_code', 'latitude', 'longitude', 'goal_id', 'query', 'country_code', 'continent_code', 'resolution', 'limit', 'transit_datetime', 'transit_location', 'transit_timezone', 'body', 'angle'],
  },
  '/api/astro-clock/election/suggest/stream': {
    methods: ['GET'],
    responseType: 'sse',
    query: ['matter', 'start', 'end', 'location', 'timezone', 'house_system_code', 'latitude', 'longitude', 'step_minutes', 'limit', 'reference_parity', 'include_series', 'include_sr_lr', 'weekday_mode', 'weekday', 'hour_start', 'hour_end', 'marriage_algorithm', 'business_algorithm', 'estate_direction', 'marriage_beta_display_mode', 'marriage_beta_scope', 'marriage_beta_current_line_id', 'marriage_beta_selected_line_id', 'marriage_beta_level_percent', 'business_beta_display_mode', 'business_beta_scope', 'business_beta_current_line_id', 'business_beta_selected_line_id', 'business_beta_level_percent', 'estate_display_mode', 'estate_scope', 'estate_current_line_id', 'estate_selected_line_id', 'estate_level_percent', 'participant_a_snap_id', 'participant_b_snap_id', 'estate_participant_snap_id', 'participant_snap_id', 'natal_snap_id', 'natal_datetime', 'natal_location', 'natal_timezone', 'consider_mode', 'level_percent', 'gender', 'hair_goal', 'haircut_type', 'surgery_sign', 'procedure', 'include_lunation_screen', 'include_fixed_stars', 'include_traditional_timing', 'business_mode', 'emphasize_commerce', 'journey_type', 'legal_action', 'action_type', 'body_parts', 'body_signs', 'procedure_type', 'prefer_fixed_asc', 'saturn_binding_ok', 'min_mercury_direct_days', 'contract_mode'],
  },
  '/api/astro-clock/chinese-astrology/bazi': { methods: ['POST'], query: [] },
  '/api/astro-clock/chinese-astrology/compatibility': { methods: ['POST'], query: [] },
  '/api/astro-clock/chinese-astrology/iching-oracle': { methods: ['POST'], query: [] },
  '/api/astro-clock/forensic': {
    methods: ['GET'],
    envelope: 'raw',
    query: ['snap_id', 'mode', 'datetime', 'location', 'timezone', 'latitude', 'longitude', 'house_system_code', 'case_type', 'abduction', 'origin', 'line_zones', 'corridor_deg'],
  },
  '/api/astro-clock/certification/rectify': { methods: ['POST'], query: [] },
});

class LicensedMcpAccessError extends Error {
  constructor(code, message, statusCode = undefined) {
    super(message);
    this.name = 'LicensedMcpAccessError';
    this.code = code;
    this.statusCode = statusCode;
  }
}

function safeDetail(payload, fallback) {
  const candidate = payload?.detail || payload?.error;
  if (typeof candidate !== 'string' || !candidate.trim()) return fallback;
  return candidate.trim().slice(0, 500);
}

function parseSseDone(text) {
  let lastError = null;
  for (const block of String(text || '').split(/\r?\n\r?\n/)) {
    const dataText = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n');
    if (!dataText) continue;
    let event;
    try {
      event = JSON.parse(dataText);
    } catch (_) {
      continue;
    }
    if (event?.type === 'done' && Object.hasOwn(event, 'data')) return event.data;
    if (event?.type === 'error') lastError = String(event.error || event.detail || 'Election calculation failed');
  }
  throw new LicensedMcpAccessError('invalid_backend_response', lastError || 'Vox Stella did not return a completed feature result.');
}

function appendValidatedQuery(requestUrl, query, allowedKeys) {
  if (query === undefined) return;
  if (!query || typeof query !== 'object' || Array.isArray(query)) {
    throw new TypeError('MCP backend query must be an object');
  }
  const allowed = new Set(allowedKeys || []);
  for (const [key, rawValue] of Object.entries(query)) {
    if (!allowed.has(key)) throw new TypeError(`MCP backend query parameter is not allowed: ${key}`);
    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    for (const value of values) {
      if (value === undefined || value === null || value === '') continue;
      if (!['string', 'number', 'boolean'].includes(typeof value)) {
        throw new TypeError(`MCP backend query parameter must be scalar: ${key}`);
      }
      requestUrl.searchParams.append(key, String(value));
    }
  }
  if (requestUrl.href.length > MAX_REQUEST_URL_LENGTH) {
    throw new TypeError('MCP backend query is too large');
  }
}

async function assertLicensedMcpAccess(licenseManager) {
  if (!licenseManager || typeof licenseManager.getStatus !== 'function') {
    throw new LicensedMcpAccessError(
      'license_unavailable',
      'Vox Stella licensing is unavailable. Start the installed licensed application once and try again.',
    );
  }
  const status = await licenseManager.getStatus().catch(() => null);
  if (!status?.active) {
    throw new LicensedMcpAccessError(
      'license_required',
      'An active Vox Stella license is required for MCP access.',
    );
  }
  const sessionToken = await licenseManager.getToken().catch(() => null);
  if (typeof sessionToken !== 'string' || !sessionToken.trim()) {
    throw new LicensedMcpAccessError(
      'license_required',
      'The Vox Stella license could not create a valid local MCP session.',
    );
  }
  return {
    active: true,
    plan: typeof status.plan === 'string' ? status.plan : undefined,
    kind: typeof status.kind === 'string' ? status.kind : undefined,
    exp: status.exp ?? null,
  };
}

function createLicensedBackendClient({
  apiBaseUrl,
  licenseManager,
  maxResponseBytes = DEFAULT_MAX_RESPONSE_BYTES,
  requestJsonImpl = requestJson,
  requestTextImpl = requestText,
  timeoutMs = DEFAULT_TIMEOUT_MS,
}) {
  let canonicalBaseUrl;
  try {
    canonicalBaseUrl = new URL(apiBaseUrl);
  } catch (_) {
    throw new TypeError('MCP backend URL must be a valid IPv4 loopback URL');
  }
  const portNumber = Number(canonicalBaseUrl.port);
  if (
    canonicalBaseUrl.protocol !== 'http:' ||
    canonicalBaseUrl.hostname !== '127.0.0.1' ||
    canonicalBaseUrl.username ||
    canonicalBaseUrl.password ||
    canonicalBaseUrl.pathname !== '/' ||
    canonicalBaseUrl.search ||
    canonicalBaseUrl.hash ||
    !Number.isInteger(portNumber) ||
    portNumber < 1 ||
    portNumber > 65535
  ) {
    throw new TypeError('MCP backend URL must use the IPv4 loopback interface');
  }
  if (!licenseManager || typeof licenseManager.getToken !== 'function') {
    throw new TypeError('licenseManager with getToken() is required');
  }

  const canonicalOrigin = canonicalBaseUrl.origin;

  return async function licensedBackendCall(pathname, body = undefined, {
    method = 'POST',
    query,
    responseType,
    signal,
    timeoutMs: callTimeoutMs,
  } = {}) {
    let requestUrl;
    try {
      requestUrl = new URL(pathname, `${canonicalOrigin}/`);
    } catch (_) {
      throw new TypeError('MCP backend path must be a valid URL pathname');
    }
    let decodedPathname;
    try {
      decodedPathname = decodeURIComponent(requestUrl.pathname);
    } catch (_) {
      throw new TypeError('MCP backend path must use valid URL encoding');
    }
    const decodedSegments = decodedPathname.split('/');
    const normalizedMethod = String(method || 'POST').trim().toUpperCase();
    const isMcpApiRoute = Object.hasOwn(MCP_CALCULATION_ROUTE_RULES, decodedPathname);
    const routeRule = MCP_CALCULATION_ROUTE_RULES[decodedPathname] || FEATURE_ROUTE_RULES[decodedPathname];
    if (
      typeof pathname !== 'string' ||
      requestUrl.origin !== canonicalOrigin ||
      requestUrl.username ||
      requestUrl.password ||
      requestUrl.search ||
      requestUrl.hash ||
      !routeRule ||
      requestUrl.pathname !== decodedPathname ||
      decodedSegments.some((segment) => segment === '.' || segment === '..')
    ) {
      throw new TypeError('MCP backend calls are restricted to the licensed feature allowlist');
    }
    if (!routeRule.methods.includes(normalizedMethod)) {
      throw new TypeError('MCP backend method is not allowed for this feature route');
    }
    if (isMcpApiRoute && query !== undefined) {
      throw new TypeError('MCP calculation API routes do not accept query parameters');
    }
    appendValidatedQuery(requestUrl, query, routeRule.query || []);
    const expectedResponseType = responseType || routeRule.responseType || 'json';
    if (expectedResponseType !== 'json' && expectedResponseType !== 'sse') {
      throw new TypeError('MCP backend responseType must be json or sse');
    }
    if (routeRule.responseType === 'sse' && expectedResponseType !== 'sse') {
      throw new TypeError('MCP streaming feature route requires SSE response handling');
    }
    const requestedTimeout = callTimeoutMs === undefined ? timeoutMs : Number(callTimeoutMs);
    if (!Number.isFinite(requestedTimeout) || requestedTimeout <= 0 || requestedTimeout > MAX_FEATURE_TIMEOUT_MS) {
      throw new TypeError('MCP backend timeout is outside the allowed range');
    }
    // Deliberately mint/refresh immediately before every request. Durable
    // license material never leaves LicenseManager or appears in MCP output.
    const sessionToken = await licenseManager.getToken().catch(() => null);
    if (typeof sessionToken !== 'string' || !sessionToken.trim()) {
      throw new LicensedMcpAccessError(
        'license_required',
        'The Vox Stella license is inactive, expired, or requires verification.',
      );
    }
    const requestImpl = expectedResponseType === 'sse' ? requestTextImpl : requestJsonImpl;
    const response = await requestImpl(requestUrl, {
      body,
      headers: { 'X-License-Token': sessionToken },
      maxResponseBytes,
      method: normalizedMethod,
      signal,
      timeoutMs: requestedTimeout,
    });
    if (response.statusCode === 402 || response.statusCode === 403) {
      throw new LicensedMcpAccessError(
        'license_required',
        'The Vox Stella license is inactive, expired, or requires verification.',
        response.statusCode,
      );
    }
    if (!response.ok) {
      let errorPayload = response.payload;
      if (typeof errorPayload === 'string') {
        try { errorPayload = JSON.parse(errorPayload); } catch (_) { errorPayload = {}; }
      }
      throw new LicensedMcpAccessError(
        errorPayload?.error || 'backend_error',
        safeDetail(errorPayload, `Vox Stella calculation failed (${response.error || response.statusCode || 'unknown error'}).`),
        response.statusCode,
      );
    }
    if (expectedResponseType === 'sse') return parseSseDone(response.payload);
    if (routeRule.envelope === 'raw') {
      if (!response.payload || typeof response.payload !== 'object' || Array.isArray(response.payload)) {
        throw new LicensedMcpAccessError(
          'invalid_backend_response',
          'Vox Stella returned an invalid feature response.',
          response.statusCode,
        );
      }
      return response.payload;
    }
    if (response.payload?.success !== true || !Object.hasOwn(response.payload, 'data')) {
      throw new LicensedMcpAccessError(
        'invalid_backend_response',
        'Vox Stella returned an invalid MCP calculation response.',
        response.statusCode,
      );
    }
    return response.payload.data;
  };
}

module.exports = {
  DEFAULT_MAX_RESPONSE_BYTES,
  DEFAULT_TIMEOUT_MS,
  LicensedMcpAccessError,
  assertLicensedMcpAccess,
  createLicensedBackendClient,
};
