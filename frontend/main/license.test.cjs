const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const nacl = require('tweetnacl');

function toB64(buffer) {
  return Buffer.from(buffer).toString('base64');
}

function loadLicenseModule(publicKeyB64) {
  process.env.LICENSE_PUBLIC_KEY_B64 = publicKeyB64;
  const modulePath = require.resolve('./license.js');
  delete require.cache[modulePath];
  return require(modulePath);
}

function signToken(secretKey, payload) {
  const body = Buffer.from(JSON.stringify(payload));
  const signature = nacl.sign.detached(new Uint8Array(body), secretKey);
  return `${toB64(signature)}.${toB64(body)}`;
}

test('perpetual plans do not require automatic entitlement refresh', () => {
  const pair = nacl.sign.keyPair();
  const publicKeyB64 = toB64(pair.publicKey);
  const { __testing } = loadLicenseModule(publicKeyB64);

  assert.equal(__testing.isPerpetualPlan('perpetual'), true);
  assert.equal(__testing.isPerpetualPlan('lifetime'), true);
  assert.equal(
    __testing.tokenNeedsEntitlementRefresh({
      plan: 'perpetual',
      next_verify_at: 1,
    }, 9_999_999_999),
    false,
  );
  assert.equal(
    __testing.tokenNeedsRefresh({
      plan: 'perpetual',
      verified_at: 1_700_000_000,
      next_verify_at: 1,
    }),
    false,
  );
});

test('renewable plans still require entitlement refresh', () => {
  const pair = nacl.sign.keyPair();
  const publicKeyB64 = toB64(pair.publicKey);
  const { __testing } = loadLicenseModule(publicKeyB64);

  assert.equal(__testing.isPerpetualPlan('weekly'), false);
  assert.equal(
    __testing.tokenNeedsEntitlementRefresh({
      plan: 'weekly',
      next_verify_at: 1,
    }, 9_999_999_999),
    true,
  );
});

test('verifySignedToken accepts perpetual tokens with stale next_verify_at and rejects stale weekly tokens', () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { __testing } = loadLicenseModule(publicKeyB64);

  const perpetualToken = signToken(pair.secretKey, {
    lic: 'LIC-PERP-1',
    plan: 'perpetual',
    device: 'device-1',
    iat: 1_700_000_000,
    verified_at: 1_700_000_000,
    next_verify_at: 1,
  });
  const weeklyToken = signToken(pair.secretKey, {
    lic: 'LIC-WEEK-1',
    plan: 'weekly',
    device: 'device-1',
    iat: 1_700_000_000,
    verified_at: 1_700_000_000,
    next_verify_at: 1,
  });

  const claims = __testing.verifySignedToken(perpetualToken);
  assert.equal(claims.plan, 'perpetual');
  assert.throws(
    () => __testing.verifySignedToken(weeklyToken),
    /refresh required/i,
  );
});

test('verifySignedToken allows stale subscription tokens until expiry', () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { __testing } = loadLicenseModule(publicKeyB64);

  const renewableToken = signToken(pair.secretKey, {
    lic: 'LIC-SUB-1',
    plan: 'pro',
    kind: 'subscription',
    device: 'device-1',
    iat: 1_700_000_000,
    verified_at: 1_700_000_000,
    next_verify_at: 1_700_000_100,
    exp: 4_100_000_000,
  });

  const claims = __testing.verifySignedToken(renewableToken);
  assert.equal(claims.kind, 'subscription');
  assert.equal(claims.exp, 4_100_000_000);
});

test('verifySignedToken accepts perpetual tokens with explicit refresh claims until expiry', () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { __testing } = loadLicenseModule(publicKeyB64);

  const renewablePerpetualToken = signToken(pair.secretKey, {
    lic: 'LIC-PERP-2',
    plan: 'pro',
    kind: 'perpetual',
    device: 'device-1',
    iat: 1_700_000_000,
    verified_at: 1_700_000_000,
    requires_entitlement_refresh: true,
    offline_capable: false,
    next_verify_at: 1_700_000_100,
    exp: 4_100_000_000,
  });

  const claims = __testing.verifySignedToken(renewablePerpetualToken);
  assert.equal(claims.kind, 'perpetual');
  assert.equal(claims.requires_entitlement_refresh, true);
});

test('getToken returns a short-lived local session token instead of the raw stored token', async () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { LicenseManager, __testing } = loadLicenseModule(publicKeyB64);

  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = toB64(crypto.randomBytes(32));
  process.env.VOX_STELLA_DEVICE_ID = 'device-1';

  const app = { isPackaged: true, getPath: () => process.cwd() };
  const manager = new LicenseManager(app);
  manager.refreshToken = async () => ({ ok: false, code: 'missing_token', error: 'No token stored' });
  manager.readStored = async () => ({
    token: signToken(pair.secretKey, {
      lic: 'LIC-RAW-1',
      plan: 'pro',
      kind: 'subscription',
      device: 'device-1',
      iat: 1_700_000_000,
      verified_at: 1_700_000_000,
      requires_entitlement_refresh: true,
      next_verify_at: 4_100_000_000,
      exp: 4_100_000_000,
    }),
  });
  manager.getDeviceId = async () => 'device-1';

  const token = await manager.getToken();
  const parts = String(token || '').split('.');
  assert.equal(parts.length, 2);
  assert.notEqual(token, (await manager.readStored()).token);
  const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf8'));
  assert.equal(payload.token_type, __testing.LOCAL_SESSION_TOKEN_TYPE);
  assert.equal(payload.device, 'device-1');
});

test('getToken rejects stored tokens bound to a different device', async () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { LicenseManager } = loadLicenseModule(publicKeyB64);

  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = toB64(crypto.randomBytes(32));
  process.env.VOX_STELLA_DEVICE_ID = 'device-1';

  const app = { isPackaged: true, getPath: () => process.cwd() };
  const manager = new LicenseManager(app);
  manager.refreshToken = async () => ({ ok: false, code: 'missing_token', error: 'No token stored' });
  manager.readStored = async () => ({
    token: signToken(pair.secretKey, {
      lic: 'LIC-RAW-2',
      plan: 'pro',
      kind: 'subscription',
      device: 'other-device',
      iat: 1_700_000_000,
      verified_at: 1_700_000_000,
      requires_entitlement_refresh: true,
      next_verify_at: 4_100_000_000,
      exp: 4_100_000_000,
    }),
  });
  manager.getDeviceId = async () => 'device-1';

  const token = await manager.getToken();
  assert.equal(token, null);
});
