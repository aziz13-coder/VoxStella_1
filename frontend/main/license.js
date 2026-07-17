// Licensing helper with server verification.
// - Secure storage via keytar (if present) or JSON file.
// - Device binding via node-machine-id (fallback to hostname/user hash).
// - Activation must contact the licensing server; perpetual entitlements can run offline after activation.
// - Renewable entitlements refresh weekly by default and remain locally valid until token expiry.
// - Max devices per key is enforced by the server.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');
const electron = tryRequire('electron');
const safeStorage = electron?.safeStorage || null;

function tryRequire(mod) { try { return require(mod); } catch (_) { return null; } }

const DEFAULT_FETCH_TIMEOUT_MS = (() => {
  const raw = Number(process.env.LICENSE_HTTP_TIMEOUT_MS || 12000);
  return Number.isFinite(raw) && raw > 0 ? raw : 12000;
})();
const DEFAULT_FETCH_RETRIES = (() => {
  const raw = Number(process.env.LICENSE_HTTP_RETRIES || 2);
  return Number.isFinite(raw) && raw >= 0 ? Math.floor(raw) : 2;
})();
const DEFAULT_FETCH_BACKOFF_MS = (() => {
  const raw = Number(process.env.LICENSE_HTTP_BACKOFF_MS || 450);
  return Number.isFinite(raw) && raw >= 0 ? raw : 450;
})();
const TOKEN_REFRESH_LEEWAY_SECONDS = (() => {
  const raw = Number(process.env.LICENSE_REFRESH_LEEWAY_SECONDS || 12 * 3600);
  return Number.isFinite(raw) && raw >= 0 ? Math.floor(raw) : 12 * 3600;
})();
const LOCAL_SESSION_TOKEN_TYPE = 'local_license_session';
const LOCAL_SESSION_SECRET_ENV = 'VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64';
const LOCAL_DEVICE_ID_ENV = 'VOX_STELLA_DEVICE_ID';
const MAX_LOCAL_SESSION_TTL_SECONDS = 5 * 60;
const LOCAL_SESSION_TTL_SECONDS = (() => {
  const raw = Number(process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_TTL_SECONDS || 180);
  return Number.isFinite(raw) && raw >= 30
    ? Math.min(Math.floor(raw), MAX_LOCAL_SESSION_TTL_SECONDS)
    : 180;
})();
const LICENSE_CLOCK_SKEW_SECONDS = 5 * 60;
const DEACTIVATION_RETRY_DELAY_SECONDS = 60;
const PAYPAL_PENDING_PLAN = 'premium-desktop-monthly';
const PAYPAL_PENDING_GRACE_SECONDS = (() => {
  const raw = Number(process.env.VOX_STELLA_PAYPAL_PENDING_GRACE_SECONDS || 24 * 3600);
  return Number.isFinite(raw) && raw >= 3600 ? Math.floor(raw) : 24 * 3600;
})();
const PAYPAL_PENDING_RETRY_TIMEOUT_MS = (() => {
  const raw = Number(process.env.VOX_STELLA_PAYPAL_PENDING_RETRY_TIMEOUT_MS || 2500);
  return Number.isFinite(raw) && raw >= 500 ? Math.floor(raw) : 2500;
})();
const LEGACY_PERPETUAL_PLAN_KEYWORDS = ['perpetual', 'lifetime', 'forever'];
const PERPETUAL_LICENSE_KINDS = new Set(['perpetual', 'lifetime', 'forever']);
const RENEWABLE_LICENSE_KINDS = new Set(['subscription', 'renewable', 'term']);
const LEGACY_OFFLINE_ACTIVATION_REVALIDATION_LIST = Object.freeze([
  Object.freeze({
    licHash: '3e8ab1bcaafadd53d24741a9efba585be7c3866648158f7ed2d6a8098f384826',
    emailHash: 'b1931f2f9a20b4474dd23c210861d9585b97ebb8e9ea4458b88a178f763e9c7c',
    deviceHash: 'b24b2979deaf7b3d1e3b055cd0c8e425c510fd183878ad26b91aa4e553f9709e',
  }),
]);
const ENTITLEMENT_REFRESH_REASONS = new Set([
  'invalid-token',
  'license-inactive',
  'device-not-activated',
  'device-mismatch',
  'subscription-inactive',
  'subscription-expired',
  'subscription-misconfigured',
]);

function toPositiveInt(value) {
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? Math.floor(num) : null;
}

function normalizePlanName(plan) {
  return String(plan || '').trim().toLowerCase();
}

function isPerpetualPlan(plan) {
  const normalized = normalizePlanName(plan);
  return LEGACY_PERPETUAL_PLAN_KEYWORDS.some((keyword) => normalized.includes(keyword));
}

function normalizeLicenseKind(kind) {
  const normalized = String(kind || '').trim().toLowerCase();
  if (!normalized) return null;
  if (RENEWABLE_LICENSE_KINDS.has(normalized)) return 'subscription';
  if (PERPETUAL_LICENSE_KINDS.has(normalized)) return 'perpetual';
  return null;
}

function sha256Normalized(value) {
  return crypto
    .createHash('sha256')
    .update(String(value || '').trim().toLowerCase())
    .digest('hex');
}

function hashMatches(value, expectedHash) {
  if (!expectedHash) return true;
  const text = String(value || '').trim();
  if (!text) return false;
  return sha256Normalized(text) === expectedHash;
}

function licenseRequiresEntitlementRefresh(payload) {
  if (typeof payload?.requires_entitlement_refresh === 'boolean') {
    return payload.requires_entitlement_refresh;
  }
  const kind = normalizeLicenseKind(payload?.kind);
  if (kind) return kind !== 'perpetual';
  return !isPerpetualPlan(payload?.plan);
}

function legacyOfflineActivationRequiresOnlineRevalidation(
  payload,
  entries = LEGACY_OFFLINE_ACTIVATION_REVALIDATION_LIST,
) {
  if (!payload || typeof payload !== 'object') return false;
  if (licenseRequiresEntitlementRefresh(payload)) return false;
  return (entries || []).some((entry) => {
    if (!entry || typeof entry !== 'object') return false;
    if (!hashMatches(payload.lic, entry.licHash)) return false;
    if (!hashMatches(payload.device, entry.deviceHash)) return false;
    if (payload.email != null && !hashMatches(payload.email, entry.emailHash)) return false;
    return true;
  });
}

function tokenNeedsEntitlementRefresh(payload, now = Math.floor(Date.now() / 1000)) {
  if (legacyOfflineActivationRequiresOnlineRevalidation(payload)) return true;
  if (!licenseRequiresEntitlementRefresh(payload)) return false;
  const nextVerifyAt = toPositiveInt(payload?.next_verify_at);
  if (!nextVerifyAt) return true;
  return nextVerifyAt <= now;
}

function tokenNeedsRefresh(payload, force = false) {
  if (force) return true;
  const now = Math.floor(Date.now() / 1000);
  if (tokenNeedsEntitlementRefresh(payload, now)) {
    return true;
  }
  const expNum = toPositiveInt(payload?.exp);
  return Boolean(expNum && (expNum - now) <= TOKEN_REFRESH_LEEWAY_SECONDS);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryableStatus(status) {
  return status === 408 || status === 429 || status >= 500;
}

function shouldInvalidateStoredTokenOnRefreshFailure(result) {
  if (!result || result.ok !== false) return false;
  const reason = String(result.reason || '').trim().toLowerCase();
  if (reason && ENTITLEMENT_REFRESH_REASONS.has(reason)) return true;
  if (result.code === 'invalid_token') return true;
  const status = Number(result.status);
  if (Number.isFinite(status) && status >= 400 && status < 500 && status !== 408 && status !== 429) {
    return true;
  }
  return false;
}

function shouldBlockStoredTokenOnRefreshFailure(result) {
  return Boolean(result && result.ok === false && result.forceRevalidation === true);
}

function paypalActivationFailureAllowsPendingActivation(result) {
  if (!result || result.ok !== false) return false;
  if (result.networkError === true) return true;
  const status = Number(result.status);
  if (!Number.isFinite(status)) return false;
  return status === 408 || status === 429 || status >= 500;
}

async function fetchWithPolicy(url, options = {}) {
  const retries = options.retries ?? DEFAULT_FETCH_RETRIES;
  const timeoutMs = options.timeoutMs ?? DEFAULT_FETCH_TIMEOUT_MS;
  const backoffMs = options.backoffMs ?? DEFAULT_FETCH_BACKOFF_MS;
  let lastErr = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        ...options,
        redirect: 'error',
        signal: controller.signal,
      });
      if (attempt < retries && isRetryableStatus(res.status)) {
        await sleep(backoffMs * (attempt + 1));
        continue;
      }
      return res;
    } catch (err) {
      lastErr = err;
      if (attempt >= retries) throw err;
      await sleep(backoffMs * (attempt + 1));
    } finally {
      clearTimeout(timeoutId);
    }
  }
  throw lastErr || new Error('Network request failed');
}

function loadLicenseConfig() {
  const locations = [];
  if (process?.resourcesPath) {
    locations.push(path.join(process.resourcesPath, 'license.config.json'));
  }
  locations.push(path.join(__dirname, '..', 'license.config.json'));
  locations.push(path.join(__dirname, 'license.config.json'));
  for (const candidate of locations) {
    try {
      if (candidate && fs.existsSync(candidate)) {
        const content = JSON.parse(fs.readFileSync(candidate, 'utf8'));
        return content || {};
      }
    } catch (err) {
      console.warn('[LicenseManager] Failed to load config', candidate, err?.message || err);
    }
  }
  return {};
}

const LICENSE_CONFIG = loadLicenseConfig();

function cleanConfigString(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function trustedLicenseServerUrl(app, options = {}) {
  const isPackaged = app?.isPackaged === true;
  const optionServerUrl = cleanConfigString(options.serverUrl);
  const configServerUrl = cleanConfigString(LICENSE_CONFIG.serverUrl);
  const envServerUrl = cleanConfigString(process.env.LICENSE_SERVER_URL);
  if (optionServerUrl) return optionServerUrl;
  if (isPackaged) return configServerUrl;
  return envServerUrl || configServerUrl;
}

function trustedPublicKeyB64(options = {}) {
  const isPackaged = options.isPackaged === true;
  const optionPublicKey = cleanConfigString(options.publicKeyB64);
  const configPublicKey = cleanConfigString(LICENSE_CONFIG.publicKeyB64);
  const envPublicKey = cleanConfigString(process.env.LICENSE_PUBLIC_KEY_B64);
  if (optionPublicKey) return optionPublicKey;
  if (isPackaged) return configPublicKey;
  return envPublicKey || configPublicKey;
}

class LicenseManager {
  constructor(app, options = {}) {
    this.app = app;
    this.keytar = tryRequire('keytar');
    this.machineIdLib = tryRequire('node-machine-id');
    this.safeStorage = safeStorage;
    this.service = 'VoxStella';
    this.account = 'license';
    this.filePath = path.join(app.getPath('userData'), 'license.json');
    const explicit = trustedLicenseServerUrl(this.app, options);
    const defaultUrl = this.app?.isPackaged
      ? 'https://license.voxstella.app'
      : 'http://127.0.0.1:8787';
    this.serverUrl = (explicit && explicit.trim()) || defaultUrl;
    this.publicKeyB64 = trustedPublicKeyB64({
      isPackaged: this.app?.isPackaged === true,
      publicKeyB64: options.publicKeyB64,
    });
    this.legacyOfflineActivationRevalidationList = Array.isArray(options.legacyOfflineActivationRevalidationList)
      ? options.legacyOfflineActivationRevalidationList
      : LEGACY_OFFLINE_ACTIVATION_REVALIDATION_LIST;
  }

  async getDeviceId() {
    try {
      if (this.machineIdLib && this.machineIdLib.machineIdSync) {
        const id = this.machineIdLib.machineIdSync({ original: true });
        return this.hash(id + '|' + this.service);
      }
    } catch (_) {}
    // Fallback: hash of hostname + platform + user
    const raw = [os.hostname(), os.platform(), os.arch(), os.userInfo().username].join('|');
    return this.hash(raw);
  }

  hash(s) { return crypto.createHash('sha256').update(String(s)).digest('hex'); }

  getLocalSessionSecret() {
    try {
      const raw = String(process.env[LOCAL_SESSION_SECRET_ENV] || '').trim();
      if (!raw) return null;
      const secret = Buffer.from(raw, 'base64');
      return secret.length >= 32 ? secret : null;
    } catch (_) {
      return null;
    }
  }

  async assertTokenMatchesDevice(token, deviceId, options = {}) {
    const data = verifySignedToken(token, {
      ...options,
      isPackaged: this.app?.isPackaged === true,
      publicKeyB64: this.publicKeyB64,
    });
    if (data.device && data.device !== deviceId) {
      throw new Error('License token device mismatch');
    }
    return data;
  }

  createRendererSessionToken(payload, deviceId) {
    const licenseId = String(payload?.lic || '').trim().toLowerCase();
    if (payload?.paypal_pending_verification === true || licenseId.startsWith('paypal-pending:')) {
      return null;
    }
    const secret = this.getLocalSessionSecret();
    const expectedDeviceId = String(process.env[LOCAL_DEVICE_ID_ENV] || '').trim();
    if (!secret || !deviceId || !expectedDeviceId || expectedDeviceId !== deviceId) {
      return null;
    }
    const now = Math.floor(Date.now() / 1000);
    const sessionExpiryCandidates = [now + LOCAL_SESSION_TTL_SECONDS];
    const requiresEntitlementRefresh = licenseRequiresEntitlementRefresh(payload);
    const sessionKind = normalizeLicenseKind(payload.kind)
      || (requiresEntitlementRefresh ? 'subscription' : 'perpetual');
    const durableExpiry = toPositiveInt(payload?.exp);
    if (durableExpiry) {
      sessionExpiryCandidates.push(durableExpiry);
    }
    if (requiresEntitlementRefresh) {
      const entitlementBoundary = toPositiveInt(payload?.next_verify_at);
      if (!entitlementBoundary) {
        return null;
      }
      // Signed subscription tokens use exp as the authoritative offline-grace
      // boundary. Legacy renewable tokens without exp remain capped at the
      // next online-verification boundary.
      if (sessionKind !== 'subscription' || !durableExpiry) {
        sessionExpiryCandidates.push(entitlementBoundary);
      }
    }
    const sessionExpiry = Math.min(...sessionExpiryCandidates);
    if (!Number.isFinite(sessionExpiry) || sessionExpiry <= now) {
      return null;
    }
    const opaqueLicenseId = `local-session:${crypto
      .createHmac('sha256', secret)
      .update(`${String(payload.lic || '').trim()}\0${deviceId}`)
      .digest('hex')}`;
    const body = {
      token_type: LOCAL_SESSION_TOKEN_TYPE,
      lic: opaqueLicenseId,
      plan: payload.plan,
      kind: sessionKind,
      device: deviceId,
      iat: now,
      exp: sessionExpiry,
      verified_at: payload.verified_at ?? null,
      next_verify_at: payload.next_verify_at ?? null,
      entitlement_exp: durableExpiry,
      requires_entitlement_refresh: requiresEntitlementRefresh,
      offline_capable: payload.offline_capable ?? !requiresEntitlementRefresh,
    };
    const bodyBuffer = Buffer.from(JSON.stringify(body));
    const signature = crypto.createHmac('sha256', secret).update(bodyBuffer).digest('base64');
    return `${signature}.${bodyBuffer.toString('base64')}`;
  }

  _encodeForFile(jsonText) {
    try {
      if (this.safeStorage && this.safeStorage.isEncryptionAvailable()) {
        const encrypted = this.safeStorage.encryptString(jsonText);
        return `enc:${encrypted.toString('base64')}`;
      }
    } catch (_) {}
    return null;
  }

  _decodeFromFile(fileText) {
    if (typeof fileText !== 'string' || !fileText.trim()) return null;
    const raw = fileText.trim();
    // Legacy plaintext fallback support.
    if (!raw.startsWith('enc:')) {
      return raw;
    }
    const payload = raw.slice(4);
    if (!payload) return null;
    try {
      if (!this.safeStorage || !this.safeStorage.isEncryptionAvailable()) {
        return null;
      }
      const decrypted = this.safeStorage.decryptString(Buffer.from(payload, 'base64'));
      return decrypted;
    } catch (_) {
      return null;
    }
  }

  async readStored() {
    // Prefer keytar
    if (this.keytar) {
      try {
        const json = await this.keytar.getPassword(this.service, this.account);
        if (json) return JSON.parse(json);
      } catch (_) {}
    }
    // Fallback file
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, 'utf8');
        const decoded = this._decodeFromFile(raw);
        if (!decoded) return null;
        const data = JSON.parse(decoded);
        return data;
      }
    } catch (_) {}
    return null;
  }

  async writeStored(obj) {
    const json = JSON.stringify(obj);
    if (this.keytar) {
      try { await this.keytar.setPassword(this.service, this.account, json); return true; } catch (_) {}
    }
    try {
      fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
      const encoded = this._encodeForFile(json);
      if (!encoded) {
        console.warn('[LicenseManager] Unable to persist token securely: safe storage unavailable.');
        return false;
      }
      fs.writeFileSync(this.filePath, encoded, 'utf8');
      return true;
    } catch (_) { return false; }
  }

  async clearStored() {
    if (this.keytar) {
      try { await this.keytar.deletePassword(this.service, this.account); } catch (_) {}
    }
    try { if (fs.existsSync(this.filePath)) fs.unlinkSync(this.filePath); } catch (_) {}
  }

  async getStatus() {
    const deviceId = await this.getDeviceId();
    let stored = await this.readStored();
    if (stored?.pendingDeactivation) {
      await this.flushPendingDeactivation({ force: false }).catch(() => null);
      stored = await this.readStored();
      if (stored?.pendingDeactivation) {
        return {
          active: false,
          deviceId,
          deactivationPending: true,
        };
      }
    }
    const refreshResult = await this.refreshToken({ force: false }).catch(() => null);
    stored = await this.readStored();
    if (refreshResult && refreshResult.ok === false && shouldInvalidateStoredTokenOnRefreshFailure(refreshResult)) {
      if (!stored?.pendingPayPalActivation) {
        await this.clearStored();
        return { active: false, deviceId };
      }
    }
    if (shouldBlockStoredTokenOnRefreshFailure(refreshResult)) {
      return {
        active: false,
        deviceId,
        error: refreshResult.error || 'License must be validated online',
      };
    }
    const token = typeof refreshResult?.token === 'string'
      ? refreshResult.token
      : stored?.token;
    if (typeof token !== 'string') {
      const pendingStatus = this.buildPendingPayPalStatus(stored?.pendingPayPalActivation, deviceId);
      if (pendingStatus) return pendingStatus;
      if (stored?.pendingPayPalActivation) await this.clearStored();
      return { active: false, deviceId };
    }
    let data;
    try {
      data = await this.assertTokenMatchesDevice(token, deviceId);
    } catch (err) {
      console.warn('[LicenseManager] Token validation failed:', err?.message || err);
      return { active: false, deviceId, error: err?.message };
    }
    const now = Math.floor(Date.now() / 1000);
    if (data.exp != null) {
      const expNum = Number(data.exp);
      if (!Number.isFinite(expNum) || expNum <= now) return { active: false, deviceId };
    }
    return {
      active: true,
      deviceId,
      plan: data.plan || 'standard',
      kind: normalizeLicenseKind(data.kind) || (licenseRequiresEntitlementRefresh(data) ? 'subscription' : 'perpetual'),
      offlineCapable: !licenseRequiresEntitlementRefresh(data),
      exp: data.exp || null,
    };
  }

  async activate({ key, email }) {
    if (!key || typeof key !== 'string' || key.trim().length < 6) {
      return { ok: false, error: 'Invalid license key' };
    }
    const pendingDeactivation = await this.flushPendingDeactivation({ force: true }).catch(() => null);
    if (pendingDeactivation?.pending) {
      return {
        ok: false,
        error: 'Reconnect to finish the previous device deactivation before activating another license',
      };
    }
    const deviceId = await this.getDeviceId();
    const server = this.serverUrl;
    if (typeof fetch !== 'function') {
      return { ok: false, error: 'fetch not available' };
    }
    const res = await fetchWithPolicy(new URL('/license/activate', server), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: key.trim(), deviceId, email: email || null }),
    });
    if (!res.ok) {
      const t = await safeJson(res);
      return { ok: false, error: t?.detail || `Activation failed (${res.status})` };
    }
    const t = await res.json();
    const token = t.token;
    try {
      await this.assertTokenMatchesDevice(token, deviceId);
    } catch (err) {
      return { ok: false, error: err?.message || 'Invalid token' };
    }
    const saved = await this.writeStored({ token });
    if (!saved) {
      return { ok: false, error: 'Unable to store license securely on this device' };
    }
    return { ok: true, status: await this.getStatus() };
  }

  buildPendingPayPalStatus(pending, deviceId, now = Math.floor(Date.now() / 1000)) {
    if (!pending || typeof pending !== 'object') return null;
    const subscriptionId = String(pending.subscriptionId || '').trim();
    const expiresAt = Number(pending.expiresAt);
    if (!subscriptionId || !Number.isFinite(expiresAt) || expiresAt <= now) {
      return null;
    }
    return {
      active: false,
      deviceId,
      plan: pending.plan || PAYPAL_PENDING_PLAN,
      kind: 'subscription',
      offlineCapable: false,
      provisional: true,
      pendingPayPalVerification: true,
      subscriptionId,
      exp: Math.floor(expiresAt),
      pendingExpiresAt: Math.floor(expiresAt),
    };
  }

  async createPendingPayPalActivation({ subscriptionId, email, reason } = {}) {
    const cleanSubscriptionId = String(subscriptionId || '').trim();
    if (!cleanSubscriptionId) {
      return { ok: false, error: 'Missing PayPal subscription ID' };
    }
    const now = Math.floor(Date.now() / 1000);
    const deviceId = await this.getDeviceId();
    const pending = {
      subscriptionId: cleanSubscriptionId,
      email: email || null,
      plan: PAYPAL_PENDING_PLAN,
      createdAt: now,
      expiresAt: now + PAYPAL_PENDING_GRACE_SECONDS,
      reason: reason || 'license-server-unreachable',
    };
    const saved = await this.writeStored({ pendingPayPalActivation: pending });
    if (!saved) {
      return { ok: false, error: 'Unable to store pending PayPal activation on this device' };
    }
    return {
      ok: true,
      provisional: true,
      pendingPayPalVerification: true,
      subscriptionId: cleanSubscriptionId,
      status: this.buildPendingPayPalStatus(pending, deviceId, now),
    };
  }

  async activatePayPalSubscriptionWithServer({ subscriptionId, email, timeoutMs = DEFAULT_FETCH_TIMEOUT_MS, retries = DEFAULT_FETCH_RETRIES } = {}) {
    const cleanSubscriptionId = typeof subscriptionId === 'string' ? subscriptionId.trim() : '';
    if (!cleanSubscriptionId) {
      return { ok: false, error: 'Missing PayPal subscription ID' };
    }
    const pendingDeactivation = await this.flushPendingDeactivation({ force: true }).catch(() => null);
    if (pendingDeactivation?.pending) {
      return {
        ok: false,
        error: 'Reconnect to finish the previous device deactivation before activating this subscription',
      };
    }
    const deviceId = await this.getDeviceId();
    const server = this.serverUrl;
    if (typeof fetch !== 'function') {
      return { ok: false, networkError: true, error: 'fetch not available' };
    }
    let res;
    try {
      res = await fetchWithPolicy(new URL('/license/activate-paypal', server), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscriptionId: cleanSubscriptionId, deviceId, email: email || null }),
        timeoutMs,
        retries,
      });
    } catch (err) {
      return { ok: false, networkError: true, error: err?.message || 'License server unavailable' };
    }
    const body = await safeJson(res);
    if (!res.ok) {
      return {
        ok: false,
        status: res.status,
        reason: typeof body?.detail === 'string' ? body.detail : null,
        error: body?.detail || `PayPal activation failed (${res.status})`,
      };
    }
    const token = body?.token;
    try {
      await this.assertTokenMatchesDevice(token, deviceId);
    } catch (err) {
      return { ok: false, error: err?.message || 'Invalid token' };
    }
    const saved = await this.writeStored({ token });
    if (!saved) {
      return { ok: false, error: 'Unable to store license securely on this device' };
    }
    return {
      ok: true,
      status: body?.status || (await this.getStatus()),
    };
  }

  async activatePayPalPurchase({ paypalId, email } = {}) {
    const cleanPayPalId = typeof paypalId === 'string' ? paypalId.trim() : '';
    if (!cleanPayPalId) {
      return { ok: false, error: 'Missing PayPal subscription or transaction ID' };
    }
    const pendingDeactivation = await this.flushPendingDeactivation({ force: true }).catch(() => null);
    if (pendingDeactivation?.pending) {
      return {
        ok: false,
        error: 'Reconnect to finish the previous device deactivation before activating this purchase',
      };
    }
    const deviceId = await this.getDeviceId();
    const server = this.serverUrl;
    if (typeof fetch !== 'function') {
      return { ok: false, networkError: true, error: 'fetch not available' };
    }
    let res;
    try {
      res = await fetchWithPolicy(new URL('/license/activate-paypal-purchase', server), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paypalId: cleanPayPalId, deviceId, email: email || null }),
      });
    } catch (err) {
      return { ok: false, networkError: true, error: err?.message || 'License server unavailable' };
    }
    const body = await safeJson(res);
    if (!res.ok) {
      return {
        ok: false,
        status: res.status,
        reason: typeof body?.detail === 'string' ? body.detail : null,
        error: body?.detail || `PayPal purchase activation failed (${res.status})`,
      };
    }
    const token = body?.token;
    try {
      await this.assertTokenMatchesDevice(token, deviceId);
    } catch (err) {
      return { ok: false, error: err?.message || 'Invalid token' };
    }
    const saved = await this.writeStored({ token });
    if (!saved) {
      return { ok: false, error: 'Unable to store license securely on this device' };
    }
    return {
      ok: true,
      status: body?.status || (await this.getStatus()),
    };
  }

  async activatePayPalSubscription({ subscriptionId, email } = {}) {
    const result = await this.activatePayPalSubscriptionWithServer({ subscriptionId, email });
    if (result?.ok || !paypalActivationFailureAllowsPendingActivation(result)) {
      return result;
    }
    return this.createPendingPayPalActivation({
      subscriptionId,
      email,
      reason: result.reason || result.error || 'license-server-unreachable',
    });
  }

  async finalizePendingPayPalActivation() {
    const stored = await this.readStored();
    const pending = stored?.pendingPayPalActivation;
    const deviceId = await this.getDeviceId();
    const pendingStatus = this.buildPendingPayPalStatus(pending, deviceId);
    if (!pendingStatus) {
      if (pending && !stored?.token) await this.clearStored();
      return { ok: false, error: 'No pending PayPal activation' };
    }
    return this.activatePayPalSubscriptionWithServer({
      subscriptionId: pending.subscriptionId,
      email: pending.email || null,
      timeoutMs: PAYPAL_PENDING_RETRY_TIMEOUT_MS,
      retries: 0,
    });
  }

  async flushPendingDeactivation({ force = false } = {}) {
    const stored = await this.readStored();
    const pending = stored?.pendingDeactivation;
    if (!pending || typeof pending !== 'object') {
      return { ok: true, completed: true, pending: false };
    }

    const token = typeof pending.token === 'string' ? pending.token : '';
    const deviceId = typeof pending.deviceId === 'string' ? pending.deviceId : '';
    if (!token || !deviceId) {
      await this.clearStored();
      return { ok: true, completed: true, pending: false };
    }

    const now = Math.floor(Date.now() / 1000);
    const nextAttemptAt = toPositiveInt(pending.nextAttemptAt);
    if (!force && nextAttemptAt && nextAttemptAt > now) {
      return { ok: false, completed: false, pending: true };
    }

    let response = null;
    let failureMessage = 'License server unavailable';
    try {
      if (typeof fetch !== 'function') {
        throw new Error('fetch not available');
      }
      response = await fetchWithPolicy(new URL('/license/deactivate', this.serverUrl), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, deviceId }),
        timeoutMs: PAYPAL_PENDING_RETRY_TIMEOUT_MS,
        retries: 0,
      });
      if (!response.ok) {
        const body = await safeJson(response);
        failureMessage = body?.detail || `Deactivation failed (${response.status})`;
      }
    } catch (err) {
      failureMessage = err?.message || failureMessage;
    }

    if (response?.ok) {
      const current = await this.readStored();
      if (
        current?.pendingDeactivation?.token === token
        && current?.pendingDeactivation?.deviceId === deviceId
      ) {
        await this.clearStored();
      }
      return { ok: true, completed: true, pending: false };
    }

    const queued = {
      ...pending,
      token,
      deviceId,
      attempts: Math.max(0, Number(pending.attempts) || 0) + 1,
      lastAttemptAt: now,
      nextAttemptAt: now + DEACTIVATION_RETRY_DELAY_SECONDS,
      lastError: failureMessage,
    };
    const saved = await this.writeStored({ pendingDeactivation: queued });
    return {
      ok: false,
      completed: false,
      pending: true,
      error: saved ? failureMessage : 'Unable to preserve the pending device deactivation',
    };
  }

  async deactivate() {
    const stored = await this.readStored();
    const token = typeof stored?.token === 'string'
      ? stored.token
      : stored?.pendingDeactivation?.token;
    if (!token) {
      await this.clearStored();
      return { ok: true, pending: false };
    }

    const deviceId = await this.getDeviceId();
    const now = Math.floor(Date.now() / 1000);
    const pendingDeactivation = {
      token,
      deviceId,
      createdAt: toPositiveInt(stored?.pendingDeactivation?.createdAt) || now,
      attempts: Math.max(0, Number(stored?.pendingDeactivation?.attempts) || 0),
    };
    const queued = await this.writeStored({ pendingDeactivation });
    if (!queued) {
      return {
        ok: false,
        pending: false,
        error: 'Unable to queue device deactivation securely',
      };
    }

    const result = await this.flushPendingDeactivation({ force: true });
    return {
      ok: true,
      pending: result.pending === true,
    };
  }

  async getToken() {
    const deviceId = await this.getDeviceId();
    const initialStored = await this.readStored();
    if (initialStored?.pendingDeactivation) {
      await this.flushPendingDeactivation({ force: false }).catch(() => null);
      return null;
    }
    const refreshed = await this.refreshToken({ force: false }).catch(() => null);
    if (refreshed?.ok && typeof refreshed.token === 'string') {
      try {
        const payload = await this.assertTokenMatchesDevice(refreshed.token, deviceId);
        return this.createRendererSessionToken(payload, deviceId);
      } catch (_) {
        await this.clearStored();
        return null;
      }
    }
    if (shouldInvalidateStoredTokenOnRefreshFailure(refreshed)) {
      const currentStored = await this.readStored();
      if (!currentStored?.pendingPayPalActivation) {
        await this.clearStored();
        return null;
      }
    }
    if (shouldBlockStoredTokenOnRefreshFailure(refreshed)) {
      return null;
    }
    const stored = await this.readStored();
    if (!stored?.token) {
      if (stored?.pendingPayPalActivation) {
        const pendingStatus = this.buildPendingPayPalStatus(stored.pendingPayPalActivation, deviceId);
        if (pendingStatus) {
          return null;
        }
        await this.clearStored();
      }
      return null;
    }
    try {
      const payload = await this.assertTokenMatchesDevice(stored.token, deviceId);
      return this.createRendererSessionToken(payload, deviceId);
    } catch (_) {
      return null;
    }
  }

  async refreshToken({ force = false } = {}) {
    const stored = await this.readStored();
    if (stored?.pendingDeactivation) {
      return {
        ok: false,
        code: 'deactivation_pending',
        error: 'Device deactivation is pending',
      };
    }
    const token = stored?.token;
    if (!token) {
      return { ok: false, code: 'missing_token', error: 'No token stored' };
    }

    let payload;
    try {
      const deviceId = await this.getDeviceId();
      payload = await this.assertTokenMatchesDevice(
        token,
        deviceId,
        { allowExpired: true, allowStaleEntitlement: true },
      );
    } catch (err) {
      return { ok: false, code: 'invalid_token', error: err?.message || 'Invalid token' };
    }

    const forceRevalidation = legacyOfflineActivationRequiresOnlineRevalidation(
      payload,
      this.legacyOfflineActivationRevalidationList,
    );
    const needsRefresh = forceRevalidation || tokenNeedsRefresh(payload, force);
    if (!needsRefresh) {
      return { ok: true, token, refreshed: false };
    }

    const deviceId = await this.getDeviceId();
    const server = this.serverUrl;
    if (typeof fetch !== 'function') {
      if (forceRevalidation) {
        return {
          ok: false,
          code: 'forced_revalidation_required',
          forceRevalidation: true,
          error: 'License must be validated online',
        };
      }
      return { ok: false, error: 'fetch not available' };
    }

    let res;
    try {
      res = await fetchWithPolicy(new URL('/license/refresh', server), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, deviceId }),
      });
    } catch (err) {
      if (forceRevalidation) {
        return {
          ok: false,
          code: 'forced_revalidation_required',
          forceRevalidation: true,
          error: 'License must be validated online',
        };
      }
      throw err;
    }
    const body = await safeJson(res);
    if (!res.ok || typeof body?.token !== 'string') {
      return {
        ok: false,
        status: res.status,
        forceRevalidation,
        reason: typeof body?.detail === 'string' ? body.detail : null,
        error: body?.detail || `Refresh failed (${res.status})`,
      };
    }

    let refreshedPayload;
    try {
      refreshedPayload = await this.assertTokenMatchesDevice(body.token, deviceId);
    } catch (err) {
      return { ok: false, error: err?.message || 'Invalid refreshed token' };
    }
    if (legacyOfflineActivationRequiresOnlineRevalidation(refreshedPayload)) {
      return {
        ok: false,
        status: 409,
        forceRevalidation: true,
        reason: 'license-entitlement-still-offline',
        error: 'License must be validated online',
      };
    }
    const saved = await this.writeStored({ token: body.token });
    if (!saved) {
      return { ok: false, error: 'Unable to store refreshed token securely on this device' };
    }
    return { ok: true, token: body.token, refreshed: true };
  }

  async verifyOnline() {
    const existingStored = await this.readStored();
    if (existingStored?.pendingDeactivation) {
      const deactivation = await this.flushPendingDeactivation({ force: true });
      if (deactivation.pending) {
        return {
          ok: false,
          error: deactivation.error || 'Device deactivation is still pending',
        };
      }
      return {
        ok: true,
        result: { status: 'deactivation-completed' },
      };
    }
    if (!existingStored?.token && existingStored?.pendingPayPalActivation) {
      const finalized = await this.finalizePendingPayPalActivation().catch((err) => ({
        ok: false,
        error: err?.message || 'PayPal activation failed',
      }));
      if (!finalized?.ok) {
        return { ok: false, error: finalized?.error || 'PayPal activation failed' };
      }
      return {
        ok: true,
        result: {
          status: 'paypal-activation-completed',
          licenseStatus: finalized.status || null,
        },
      };
    }
    const refreshResult = await this.refreshToken({ force: true }).catch(() => null);
    if (refreshResult && refreshResult.ok === false) {
      if (shouldInvalidateStoredTokenOnRefreshFailure(refreshResult)) {
        await this.clearStored();
      }
      return { ok: false, error: refreshResult.error || 'Token refresh failed' };
    }
    const stored = await this.readStored();
    const deviceId = await this.getDeviceId();
    if (!stored?.token) {
      return { ok: false, error: 'No token stored' };
    }
    const server = this.serverUrl;
    if (typeof fetch !== 'function') {
      return { ok: false, error: 'fetch not available' };
    }
    const res = await fetchWithPolicy(new URL('/license/verify', server), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: stored.token, deviceId }),
    });
    const body = await safeJson(res);
    if (!res.ok) {
      return { ok: false, error: body?.detail || body?.reason || `Verify failed (${res.status})` };
    }
    if (body && body.allowed === false) {
      // Server explicitly denied entitlement; drop local token to force re-activation.
      await this.clearStored();
      return { ok: false, error: body.reason || 'License is not allowed', result: body };
    }
    return { ok: true, result: body };
  }
}

// === Ed25519 verification helpers ===
function decodeB64(s) {
  return Buffer.from(s, 'base64');
}

// Replace this with your real base64-encoded public key (from licensing_server/keys/generate_keys.py output)
// Embedded public key (base64) for offline signature verification.
// Replace with your production key when deploying a public server.
const DEFAULT_PUBLIC_KEY_B64 = trustedPublicKeyB64();
if (!DEFAULT_PUBLIC_KEY_B64) {
  console.warn('[LicenseManager] LICENSE_PUBLIC_KEY_B64 is not configured. Licensing actions will fail until it is provided.');
}

function verifySignedToken(token, options = {}) {
  const allowExpired = options?.allowExpired === true;
  const allowStaleEntitlement = options?.allowStaleEntitlement === true;
  const publicKeyB64 = trustedPublicKeyB64({
    isPackaged: options?.isPackaged === true,
    publicKeyB64: options?.publicKeyB64,
  });
  if (!publicKeyB64) {
    throw new Error('LICENSE_PUBLIC_KEY_B64 is not configured');
  }
  if (!token || typeof token !== 'string') {
    throw new Error('License token is missing');
  }

  const parts = token.split('.');
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error('License token is malformed');
  }

  try {
    const [sigB64, bodyB64] = parts;
    const sig = decodeB64(sigB64);
    const body = decodeB64(bodyB64);
    const sodium = require('tweetnacl');
    const pub = Buffer.from(publicKeyB64, 'base64');
    const ok = sodium.sign.detached.verify(new Uint8Array(body), new Uint8Array(sig), new Uint8Array(pub));
    if (!ok) {
      throw new Error('Invalid license token signature');
    }
    const payload = JSON.parse(body.toString('utf-8'));
    if (!payload || typeof payload !== 'object') {
      throw new Error('Invalid license token payload');
    }
    if (typeof payload.lic !== 'string' || !payload.lic.trim()) {
      throw new Error('Invalid license token claim: lic');
    }
    if (typeof payload.device !== 'string' || !payload.device.trim()) {
      throw new Error('Invalid license token claim: device');
    }
    if (typeof payload.plan !== 'string' || !payload.plan.trim()) {
      throw new Error('Invalid license token claim: plan');
    }
    const normalizedKind = normalizeLicenseKind(payload.kind);
    if (payload.kind != null && !normalizedKind) {
      throw new Error('Invalid license token claim: kind');
    }
    if (
      payload.requires_entitlement_refresh != null &&
      typeof payload.requires_entitlement_refresh !== 'boolean'
    ) {
      throw new Error('Invalid license token claim: requires_entitlement_refresh');
    }
    if (payload.offline_capable != null && typeof payload.offline_capable !== 'boolean') {
      throw new Error('Invalid license token claim: offline_capable');
    }
    const iatNum = Number(payload.iat);
    if (!Number.isFinite(iatNum) || iatNum <= 0) {
      throw new Error('Invalid license token claim: iat');
    }
    const verifiedAtNum = toPositiveInt(payload.verified_at);
    const nextVerifyAtNum = toPositiveInt(payload.next_verify_at);
    const requiresEntitlementRefresh = licenseRequiresEntitlementRefresh(payload);
    if (!verifiedAtNum) {
      throw new Error('License entitlement refresh required');
    }
    const now = Math.floor(Date.now() / 1000);
    if (iatNum > now + LICENSE_CLOCK_SKEW_SECONDS) {
      throw new Error('License token issue time is in the future');
    }
    if (verifiedAtNum > now + LICENSE_CLOCK_SKEW_SECONDS) {
      throw new Error('License verification time is in the future');
    }
    if (
      requiresEntitlementRefresh &&
      (!nextVerifyAtNum || nextVerifyAtNum < verifiedAtNum) &&
      !allowStaleEntitlement
    ) {
      throw new Error('License entitlement refresh required');
    }
    if (payload.exp != null) {
      const expNum = Number(payload.exp);
      if (!Number.isFinite(expNum) || expNum <= 0) {
        throw new Error('Invalid license token claim: exp');
      }
      if (!allowExpired) {
        if (expNum <= now) {
          throw new Error('License token has expired');
        }
      }
    }
    if (!allowStaleEntitlement && payload.exp == null) {
      if (requiresEntitlementRefresh && nextVerifyAtNum <= now) {
        throw new Error('License entitlement refresh required');
      }
    }
    return payload;
  } catch (e) {
    throw new Error(e?.message || 'License token validation failed');
  }
}

async function safeJson(res) {
  try { return await res.json(); } catch { return null; }
}

module.exports = { LicenseManager };
module.exports.__testing = {
  LOCAL_SESSION_TOKEN_TYPE,
  MAX_LOCAL_SESSION_TTL_SECONDS,
  LICENSE_CLOCK_SKEW_SECONDS,
  isPerpetualPlan,
  normalizeLicenseKind,
  licenseRequiresEntitlementRefresh,
  legacyOfflineActivationRequiresOnlineRevalidation,
  tokenNeedsEntitlementRefresh,
  tokenNeedsRefresh,
  fetchWithPolicy,
  verifySignedToken,
};
