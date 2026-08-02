const { requestJson } = require('../backend-http');

const DEFAULT_TIMEOUT_MS = 30000;
const DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024;

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

  return async function licensedBackendCall(pathname, body = undefined, { method = 'POST', signal } = {}) {
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
    if (
      typeof pathname !== 'string' ||
      requestUrl.origin !== canonicalOrigin ||
      requestUrl.username ||
      requestUrl.password ||
      requestUrl.search ||
      requestUrl.hash ||
      !requestUrl.pathname.startsWith('/api/mcp/') ||
      !decodedPathname.startsWith('/api/mcp/') ||
      decodedSegments.some((segment) => segment === '.' || segment === '..')
    ) {
      throw new TypeError('MCP backend calls are restricted to /api/mcp/*');
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
    const response = await requestJsonImpl(requestUrl, {
      body,
      headers: { 'X-License-Token': sessionToken },
      maxResponseBytes,
      method,
      signal,
      timeoutMs,
    });
    if (response.statusCode === 402 || response.statusCode === 403) {
      throw new LicensedMcpAccessError(
        'license_required',
        'The Vox Stella license is inactive, expired, or requires verification.',
        response.statusCode,
      );
    }
    if (!response.ok) {
      throw new LicensedMcpAccessError(
        response.payload?.error || 'backend_error',
        safeDetail(response.payload, `Vox Stella calculation failed (${response.error || response.statusCode || 'unknown error'}).`),
        response.statusCode,
      );
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
