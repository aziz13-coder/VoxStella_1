const path = require('path');
const crypto = require('crypto');
const { fileURLToPath } = require('url');

const MAX_EXTERNAL_URL_CHARS = 4096;
const MAX_REPORT_HTML_BYTES = 4 * 1024 * 1024;
const PRODUCTION_LICENSE_SERVER_ORIGIN = 'https://license.voxstella.app';
const PRODUCTION_LICENSE_PUBLIC_KEY_SHA256 =
  '76774d7d0fce6527c3ce8595bd9a8d6ddfe5aea17c61d94b00156054b866cce6';
const REPORT_PAGE_SIZES = new Set(['A3', 'A4', 'A5', 'Letter', 'Legal', 'Tabloid']);
const REPORT_CONTENT_SECURITY_POLICY = [
  "default-src 'none'",
  "script-src 'none'",
  "style-src 'unsafe-inline'",
  'img-src data:',
  'font-src data:',
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-src 'none'",
].join('; ');

function normalizeComparablePath(filePath) {
  const resolved = path.resolve(String(filePath || ''));
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
}

function isAllowedExternalUrl(rawUrl) {
  if (typeof rawUrl !== 'string') return false;
  const value = rawUrl.trim();
  if (!value || value.length > MAX_EXTERNAL_URL_CHARS || /[\u0000-\u001f\u007f]/.test(value)) {
    return false;
  }
  try {
    const parsed = new URL(value);
    if (parsed.protocol === 'https:') {
      return Boolean(parsed.hostname) && !parsed.username && !parsed.password;
    }
    if (parsed.protocol === 'mailto:') {
      return Boolean(parsed.pathname) && !/%(?:0a|0d)/i.test(value);
    }
    return false;
  } catch (_) {
    return false;
  }
}

function buildPayPalCheckoutUrl(serverUrl) {
  try {
    const server = new URL(String(serverUrl || '').trim());
    if (server.protocol !== 'https:' || !server.hostname || server.username || server.password) {
      return null;
    }
    const checkoutUrl = new URL('/checkout/desktop-monthly', server).href;
    return isAllowedExternalUrl(checkoutUrl) ? checkoutUrl : null;
  } catch (_) {
    return null;
  }
}

function validatePackagedLicenseConfig(config, {
  expectedPublicKeySha256,
  expectedServerOrigin,
} = {}) {
  if (!config || typeof config !== 'object' || Array.isArray(config)) {
    throw new Error('Bundled license configuration is missing');
  }
  const serverUrl = String(config.serverUrl || '').trim();
  const publicKeyB64 = String(config.publicKeyB64 || '').trim();
  let parsedServer;
  try {
    parsedServer = new URL(serverUrl);
  } catch (_) {
    throw new Error('Bundled license server URL is invalid');
  }
  if (
    parsedServer.protocol !== 'https:' ||
    !parsedServer.hostname ||
    parsedServer.username ||
    parsedServer.password
  ) {
    throw new Error('Bundled license server URL must be credential-free HTTPS');
  }
  if (
    !/^[A-Za-z0-9+/]+={0,2}$/.test(publicKeyB64) ||
    publicKeyB64.length % 4 !== 0
  ) {
    throw new Error('Bundled license public key is invalid');
  }
  let publicKey;
  try {
    publicKey = Buffer.from(publicKeyB64, 'base64');
  } catch (_) {
    throw new Error('Bundled license public key is invalid');
  }
  if (
    publicKey.length !== 32 ||
    publicKey.toString('base64').replace(/=+$/, '') !== publicKeyB64.replace(/=+$/, '')
  ) {
    throw new Error('Bundled license public key must be a 32-byte Ed25519 key');
  }
  if (
    expectedPublicKeySha256 != null &&
    crypto.createHash('sha256').update(publicKey).digest('hex') !==
      String(expectedPublicKeySha256).toLowerCase()
  ) {
    throw new Error('Bundled license public key does not match the production trust root');
  }
  const normalizedServerUrl = parsedServer.href.replace(/\/$/, '');
  if (
    expectedServerOrigin != null &&
    normalizedServerUrl !== String(expectedServerOrigin).replace(/\/$/, '')
  ) {
    throw new Error('Bundled license server URL does not match the production trust root');
  }
  return {
    serverUrl: normalizedServerUrl,
    publicKeyB64,
  };
}

function isAllowedRendererUrl(rawUrl, {
  isPackaged,
  packagedEntryPath,
  developmentOrigins = ['http://localhost:5173'],
} = {}) {
  if (typeof rawUrl !== 'string' || !rawUrl.trim()) return false;
  try {
    const parsed = new URL(rawUrl);
    if (isPackaged) {
      if (parsed.protocol !== 'file:' || !packagedEntryPath) return false;
      const requestedPath = normalizeComparablePath(fileURLToPath(parsed));
      const expectedPath = normalizeComparablePath(packagedEntryPath);
      return requestedPath === expectedPath;
    }
    if (parsed.protocol !== 'http:') return false;
    const allowedOrigins = new Set(developmentOrigins);
    if (!allowedOrigins.has(parsed.origin)) return false;
    return parsed.pathname === '/' || parsed.pathname === '/index.html';
  } catch (_) {
    return false;
  }
}

function injectReportContentSecurityPolicy(input) {
  let html = String(input || '');
  html = html.replace(
    /<meta\b[^>]*http-equiv\s*=\s*(?:"content-security-policy"|'content-security-policy'|content-security-policy)[^>]*>/gi,
    '',
  );
  html = html.replace(/<base\b[^>]*>/gi, '');
  const meta = `<meta http-equiv="Content-Security-Policy" content="${REPORT_CONTENT_SECURITY_POLICY}">`;
  if (/<head\b[^>]*>/i.test(html)) {
    return html.replace(/<head\b[^>]*>/i, (head) => `${head}${meta}`);
  }
  return `${meta}${html}`;
}

function sanitizeReportHtml(input) {
  let html = String(input || '');
  html = html.replace(/<script\b[\s\S]*?>[\s\S]*?<\/script\s*>/gi, '');
  html = html.replace(/<(?:iframe|frame|object|embed|webview)\b[\s\S]*?(?:\/>|>[\s\S]*?<\/(?:iframe|frame|object|embed|webview)\s*>)/gi, '');
  html = html.replace(/<link\b[^>]*>/gi, '');
  html = html.replace(
    /<meta\b[^>]*http-equiv\s*=\s*(?:"refresh"|'refresh'|refresh)[^>]*>/gi,
    '',
  );
  html = html.replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '');
  html = html.replace(/\bjavascript\s*:/gi, '');
  html = html.replace(/@import\b[^;]*(?:;|$)/gi, '');
  html = html.replace(/url\s*\(\s*(?!['"]?data:)[^)]+\)/gi, 'none');
  return injectReportContentSecurityPolicy(html);
}

function sanitizePdfDefaultPath(value, fallback = 'Report.pdf') {
  const raw = String(value || fallback).trim() || fallback;
  const safe = raw.replace(/[<>:"/\\|?*\x00-\x1F]/g, '_').slice(0, 180) || 'Report.pdf';
  return /\.pdf$/i.test(safe) ? safe : `${safe}.pdf`;
}

function sanitizeDialogTitle(value, fallback = 'Save Report') {
  const normalized = String(value || fallback)
    .replace(/[\u0000-\u001f\u007f]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 120);
  return normalized || fallback;
}

function validateReportPayload(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('Invalid report payload');
  }
  const html = typeof payload.html === 'string' ? payload.html : '';
  if (!html.trim()) throw new Error('Empty report HTML');
  if (Buffer.byteLength(html, 'utf8') > MAX_REPORT_HTML_BYTES) {
    throw new Error(`Report HTML exceeds ${MAX_REPORT_HTML_BYTES} bytes`);
  }
  const requestedPageSize = payload.pageSize == null ? 'A4' : String(payload.pageSize);
  if (!REPORT_PAGE_SIZES.has(requestedPageSize)) {
    throw new Error('Unsupported report page size');
  }
  return {
    html: sanitizeReportHtml(html),
    pageSize: requestedPageSize,
    title: sanitizeDialogTitle(payload.title, 'Save Forensic Report'),
    defaultPath: sanitizePdfDefaultPath(payload.defaultPath, 'ForensicReport.pdf'),
  };
}

module.exports = {
  MAX_REPORT_HTML_BYTES,
  PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
  PRODUCTION_LICENSE_SERVER_ORIGIN,
  REPORT_CONTENT_SECURITY_POLICY,
  REPORT_PAGE_SIZES,
  buildPayPalCheckoutUrl,
  isAllowedExternalUrl,
  isAllowedRendererUrl,
  sanitizeDialogTitle,
  sanitizePdfDefaultPath,
  sanitizeReportHtml,
  validatePackagedLicenseConfig,
  validateReportPayload,
};
