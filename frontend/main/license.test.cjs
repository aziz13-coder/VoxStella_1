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

test('packaged verification ignores environment public key overrides', () => {
  const envSeed = crypto.randomBytes(32);
  const envPair = nacl.sign.keyPair.fromSeed(envSeed);
  const trustedSeed = crypto.randomBytes(32);
  const trustedPair = nacl.sign.keyPair.fromSeed(trustedSeed);
  const { __testing } = loadLicenseModule(toB64(envPair.publicKey));

  const payload = {
    lic: 'LIC-ENV-ATTACK',
    plan: 'pro',
    kind: 'perpetual',
    device: 'device-1',
    iat: 1_700_000_000,
    verified_at: 1_700_000_000,
    offline_capable: true,
  };
  const envSignedToken = signToken(envPair.secretKey, payload);
  const trustedToken = signToken(trustedPair.secretKey, payload);

  assert.throws(
    () => __testing.verifySignedToken(envSignedToken, {
      isPackaged: true,
      publicKeyB64: toB64(trustedPair.publicKey),
    }),
    /signature/i,
  );
  const claims = __testing.verifySignedToken(trustedToken, {
    isPackaged: true,
    publicKeyB64: toB64(trustedPair.publicKey),
  });
  assert.equal(claims.lic, 'LIC-ENV-ATTACK');
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

test('verifySignedToken rejects tokens issued after the allowed clock skew', () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { __testing } = loadLicenseModule(publicKeyB64);
  const originalDateNow = Date.now;
  const now = 2_000_000_000;
  Date.now = () => now * 1000;

  try {
    const futureToken = signToken(pair.secretKey, {
      lic: 'LIC-FUTURE-1',
      plan: 'perpetual',
      kind: 'perpetual',
      device: 'device-1',
      iat: now + __testing.LICENSE_CLOCK_SKEW_SECONDS + 1,
      verified_at: now,
      offline_capable: true,
    });

    assert.throws(
      () => __testing.verifySignedToken(futureToken),
      /future/i,
    );
  } finally {
    Date.now = originalDateNow;
  }
});

test('renderer sessions are opaque, capped, and bounded by the entitlement', () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const originalDateNow = Date.now;
  const previousTtl = process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_TTL_SECONDS;
  const previousSecret = process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64;
  const previousDevice = process.env.VOX_STELLA_DEVICE_ID;
  const now = 2_000_000_000;

  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_TTL_SECONDS = '86400';
  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = toB64(crypto.randomBytes(32));
  process.env.VOX_STELLA_DEVICE_ID = 'device-opaque';
  Date.now = () => now * 1000;

  try {
    const { LicenseManager, __testing } = loadLicenseModule(publicKeyB64);
    const manager = new LicenseManager(
      { isPackaged: true, getPath: () => process.cwd() },
      { publicKeyB64 },
    );
    const canonicalLicenseKey = 'LIC-DO-NOT-EXPOSE';
    const token = manager.createRendererSessionToken({
      lic: canonicalLicenseKey,
      plan: 'pro',
      kind: 'subscription',
      device: 'device-opaque',
      iat: now - 10,
      verified_at: now - 10,
      next_verify_at: now + 60,
      exp: now + 600,
      requires_entitlement_refresh: true,
      offline_capable: false,
    }, 'device-opaque');
    const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64').toString('utf8'));

    assert.match(payload.lic, /^local-session:[a-f0-9]{64}$/);
    assert.notEqual(payload.lic, canonicalLicenseKey);
    assert.equal(payload.exp, now + __testing.MAX_LOCAL_SESSION_TTL_SECONDS);
    assert.equal(payload.entitlement_exp, now + 600);
    assert.ok(payload.exp - payload.iat <= __testing.MAX_LOCAL_SESSION_TTL_SECONDS);
    assert.equal(Buffer.from(token.split('.')[1], 'base64').includes(canonicalLicenseKey), false);
  } finally {
    Date.now = originalDateNow;
    if (previousTtl == null) delete process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_TTL_SECONDS;
    else process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_TTL_SECONDS = previousTtl;
    if (previousSecret == null) delete process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64;
    else process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = previousSecret;
    if (previousDevice == null) delete process.env.VOX_STELLA_DEVICE_ID;
    else process.env.VOX_STELLA_DEVICE_ID = previousDevice;
  }
});

test('renderer sessions remain available during a signed subscription offline grace window', async () => {
  const pair = nacl.sign.keyPair();
  const publicKeyB64 = toB64(pair.publicKey);
  const originalDateNow = Date.now;
  const previousSecret = process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64;
  const previousDevice = process.env.VOX_STELLA_DEVICE_ID;
  const now = 2_000_000_000;

  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = toB64(crypto.randomBytes(32));
  process.env.VOX_STELLA_DEVICE_ID = 'device-grace';
  Date.now = () => now * 1000;

  try {
    const { LicenseManager, __testing } = loadLicenseModule(publicKeyB64);
    const durableExpiry = now + 120;
    const durableToken = signToken(pair.secretKey, {
      lic: 'LIC-GRACE-1',
      plan: 'pro',
      kind: 'subscription',
      device: 'device-grace',
      iat: now - 604_900,
      verified_at: now - 604_900,
      next_verify_at: now - 100,
      exp: durableExpiry,
      requires_entitlement_refresh: true,
      offline_capable: false,
    });
    const manager = new LicenseManager(
      { isPackaged: true, getPath: () => process.cwd() },
      { publicKeyB64 },
    );
    manager.refreshToken = async () => ({ ok: false, networkError: true, error: 'offline' });
    manager.readStored = async () => ({ token: durableToken });
    manager.getDeviceId = async () => 'device-grace';

    const sessionToken = await manager.getToken();
    assert.ok(sessionToken);
    const payload = JSON.parse(Buffer.from(sessionToken.split('.')[1], 'base64').toString('utf8'));
    assert.equal(payload.token_type, __testing.LOCAL_SESSION_TOKEN_TYPE);
    assert.equal(payload.next_verify_at, now - 100);
    assert.equal(payload.entitlement_exp, durableExpiry);
    assert.equal(payload.exp, durableExpiry);
    assert.ok(payload.exp - payload.iat <= __testing.MAX_LOCAL_SESSION_TTL_SECONDS);
  } finally {
    Date.now = originalDateNow;
    if (previousSecret == null) delete process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64;
    else process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = previousSecret;
    if (previousDevice == null) delete process.env.VOX_STELLA_DEVICE_ID;
    else process.env.VOX_STELLA_DEVICE_ID = previousDevice;
  }
});

test('renderer sessions fail closed after subscription grace expiry', () => {
  const pair = nacl.sign.keyPair();
  const publicKeyB64 = toB64(pair.publicKey);
  const originalDateNow = Date.now;
  const previousSecret = process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64;
  const previousDevice = process.env.VOX_STELLA_DEVICE_ID;
  const now = 2_000_000_000;

  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = toB64(crypto.randomBytes(32));
  process.env.VOX_STELLA_DEVICE_ID = 'device-expired';
  Date.now = () => now * 1000;

  try {
    const { LicenseManager } = loadLicenseModule(publicKeyB64);
    const manager = new LicenseManager(
      { isPackaged: true, getPath: () => process.cwd() },
      { publicKeyB64 },
    );
    const sessionToken = manager.createRendererSessionToken({
      lic: 'LIC-EXPIRED-1',
      plan: 'pro',
      kind: 'subscription',
      device: 'device-expired',
      iat: now - 605_000,
      verified_at: now - 605_000,
      next_verify_at: now - 200,
      exp: now,
      requires_entitlement_refresh: true,
      offline_capable: false,
    }, 'device-expired');

    assert.equal(sessionToken, null);
  } finally {
    Date.now = originalDateNow;
    if (previousSecret == null) delete process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64;
    else process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = previousSecret;
    if (previousDevice == null) delete process.env.VOX_STELLA_DEVICE_ID;
    else process.env.VOX_STELLA_DEVICE_ID = previousDevice;
  }
});

test('getToken returns a short-lived local session token instead of the raw stored token', async () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { LicenseManager, __testing } = loadLicenseModule(publicKeyB64);

  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = toB64(crypto.randomBytes(32));
  process.env.VOX_STELLA_DEVICE_ID = 'device-1';

  const app = { isPackaged: true, getPath: () => process.cwd() };
  const manager = new LicenseManager(app, { publicKeyB64 });
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
  assert.match(payload.lic, /^local-session:[a-f0-9]{64}$/);
  assert.notEqual(payload.lic, 'LIC-RAW-1');
});

test('getToken rejects stored tokens bound to a different device', async () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { LicenseManager } = loadLicenseModule(publicKeyB64);

  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = toB64(crypto.randomBytes(32));
  process.env.VOX_STELLA_DEVICE_ID = 'device-1';

  const app = { isPackaged: true, getPath: () => process.cwd() };
  const manager = new LicenseManager(app, { publicKeyB64 });
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

test('known legacy offline activations are forced back through online revalidation', async () => {
  const seed = crypto.randomBytes(32);
  const pair = nacl.sign.keyPair.fromSeed(seed);
  const publicKeyB64 = toB64(pair.publicKey);
  const { LicenseManager, __testing } = loadLicenseModule(publicKeyB64);

  const lic = 'FAKE-LEGACY-OFFLINE';
  const device = 'fake-device';
  const forcedEntry = {
    licHash: crypto.createHash('sha256').update(lic.toLowerCase()).digest('hex'),
    deviceHash: crypto.createHash('sha256').update(device.toLowerCase()).digest('hex'),
  };
  const token = signToken(pair.secretKey, {
    lic,
    plan: 'perpetual',
    kind: 'perpetual',
    device,
    iat: 1_700_000_000,
    verified_at: 1_700_000_000,
    offline_capable: true,
  });

  const claims = __testing.verifySignedToken(token);
  assert.equal(
    __testing.legacyOfflineActivationRequiresOnlineRevalidation(claims, [forcedEntry]),
    true,
  );

  const originalFetch = global.fetch;
  let cleared = false;
  global.fetch = async () => ({
    ok: false,
    status: 403,
    json: async () => ({ detail: 'subscription-expired' }),
  });
  try {
    const app = { isPackaged: true, getPath: () => process.cwd() };
    const manager = new LicenseManager(app, {
      publicKeyB64,
      legacyOfflineActivationRevalidationList: [forcedEntry],
    });
    manager.readStored = async () => ({ token });
    manager.clearStored = async () => {
      cleared = true;
    };
    manager.getDeviceId = async () => device;

    const status = await manager.getStatus();

    assert.equal(status.active, false);
    assert.equal(cleared, true);
  } finally {
    global.fetch = originalFetch;
  }
});

test('offline deactivation locks locally, queues server cleanup, and later completes', async () => {
  const pair = nacl.sign.keyPair();
  const publicKeyB64 = toB64(pair.publicKey);
  const { LicenseManager } = loadLicenseModule(publicKeyB64);
  const originalFetch = global.fetch;
  let stored = { token: 'signed-durable-token' };
  let fetchCalls = 0;

  const app = { isPackaged: true, getPath: () => process.cwd() };
  const manager = new LicenseManager(app, {
    serverUrl: 'https://license.example.test',
    publicKeyB64,
  });
  manager.getDeviceId = async () => 'device-queued';
  manager.readStored = async () => stored;
  manager.writeStored = async (payload) => {
    stored = payload;
    return true;
  };
  manager.clearStored = async () => {
    stored = null;
  };

  global.fetch = async () => {
    fetchCalls += 1;
    throw new Error('offline');
  };

  try {
    const result = await manager.deactivate();
    assert.equal(result.ok, true);
    assert.equal(result.pending, true);
    assert.equal(stored.token, undefined);
    assert.equal(stored.pendingDeactivation.token, 'signed-durable-token');

    const status = await manager.getStatus();
    assert.equal(status.active, false);
    assert.equal(status.deactivationPending, true);
    assert.equal(fetchCalls, 1);

    global.fetch = async () => {
      fetchCalls += 1;
      return {
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      };
    };
    const completed = await manager.flushPendingDeactivation({ force: true });
    assert.equal(completed.completed, true);
    assert.equal(stored, null);
    assert.equal(fetchCalls, 2);
  } finally {
    global.fetch = originalFetch;
  }
});

test('license HTTP policy refuses redirects so credential bodies cannot leave the trust origin', async () => {
  const pair = nacl.sign.keyPair();
  const publicKeyB64 = toB64(pair.publicKey);
  const { __testing } = loadLicenseModule(publicKeyB64);
  const originalFetch = global.fetch;
  let observedOptions = null;
  global.fetch = async (_url, options) => {
    observedOptions = options;
    return {
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    };
  };

  try {
    await __testing.fetchWithPolicy(
      new URL('https://license.example.test/license/refresh'),
      {
        method: 'POST',
        body: '{"token":"durable-secret"}',
        redirect: 'follow',
        retries: 0,
      },
    );
    assert.equal(observedOptions.redirect, 'error');
    assert.equal(observedOptions.method, 'POST');
  } finally {
    global.fetch = originalFetch;
  }
});
