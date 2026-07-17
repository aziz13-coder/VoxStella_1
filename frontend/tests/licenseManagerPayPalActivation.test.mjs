import nacl from 'tweetnacl';
import { createRequire } from 'module';
import { randomBytes } from 'node:crypto';

const require = createRequire(import.meta.url);
const originalFetch = global.fetch;
const originalDateNow = Date.now;

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function signToken(secretKey, payload) {
  const body = Buffer.from(JSON.stringify(payload, Object.keys(payload).sort()));
  const sig = nacl.sign.detached(new Uint8Array(body), secretKey);
  return `${Buffer.from(sig).toString('base64')}.${body.toString('base64')}`;
}

const keyPair = nacl.sign.keyPair();
process.env.LICENSE_PUBLIC_KEY_B64 = Buffer.from(keyPair.publicKey).toString('base64');

const { LicenseManager } = require('../main/license.js');
Date.now = () => 1_800_000_000 * 1000;

const token = signToken(keyPair.secretKey, {
  lic: 'LIC-PAYPAL-1',
  plan: 'premium-desktop-monthly',
  kind: 'subscription',
  device: 'device-1',
  iat: 1_800_000_000,
  verified_at: 1_800_000_000,
  requires_entitlement_refresh: true,
  next_verify_at: 1_800_604_800,
  exp: 1_800_777_600,
});

let capturedUrl;
let capturedOptions;
let storedPayload;
global.fetch = async (url, options) => {
  capturedUrl = new URL(String(url));
  capturedOptions = options;
  return {
    ok: true,
    json: async () => ({ token, licenseKey: 'LIC-PAYPAL-1' }),
  };
};

const manager = new LicenseManager(
  { getPath: () => process.cwd(), isPackaged: true },
  { serverUrl: 'https://license.example.test', publicKeyB64: Buffer.from(keyPair.publicKey).toString('base64') },
);
manager.getDeviceId = async () => 'device-1';
manager.writeStored = async (payload) => {
  storedPayload = payload;
  return true;
};
manager.getStatus = async () => ({ active: true, plan: 'premium-desktop-monthly' });

const result = await manager.activatePayPalSubscription({ subscriptionId: 'I-SUBSCRIPTION-123' });
const requestBody = JSON.parse(capturedOptions.body);

assert(result.ok === true, 'PayPal activation should succeed');
assert(!Object.hasOwn(result, 'licenseKey'), 'PayPal activation must not expose the canonical license key');
assert(capturedUrl.pathname === '/license/activate-paypal', 'PayPal activation should use the PayPal license endpoint');
assert(requestBody.subscriptionId === 'I-SUBSCRIPTION-123', 'PayPal activation should send the subscription id');
assert(requestBody.deviceId === 'device-1', 'PayPal activation should bind the token to this device');
assert(storedPayload.token === token, 'PayPal activation should persist the returned token');

const pendingNow = 1_800_000_000;
Date.now = () => pendingNow * 1000;
process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = Buffer.from(randomBytes(32)).toString('base64');
process.env.VOX_STELLA_DEVICE_ID = 'device-pending';
let pendingStoredPayload;
let pendingFetchCalls = 0;
global.fetch = async () => {
  pendingFetchCalls += 1;
  throw new Error('license server offline');
};

const pendingManager = new LicenseManager(
  { getPath: () => process.cwd(), isPackaged: true },
  { serverUrl: 'https://license.example.test', publicKeyB64: Buffer.from(keyPair.publicKey).toString('base64') },
);
pendingManager.getDeviceId = async () => 'device-pending';
pendingManager.readStored = async () => pendingStoredPayload || null;
pendingManager.writeStored = async (payload) => {
  pendingStoredPayload = payload;
  return true;
};
pendingManager.clearStored = async () => {
  pendingStoredPayload = null;
};

const pendingResult = await pendingManager.activatePayPalSubscription({ subscriptionId: 'I-PENDING-123' });
assert(pendingResult.ok === true, 'offline PayPal activation should create a pending activation');
assert(pendingResult.provisional === true, 'offline PayPal activation should be marked provisional');
assert(
  pendingResult.status.pendingPayPalVerification === true,
  'pending PayPal status should require later verification',
);
assert(
  pendingStoredPayload.pendingPayPalActivation.subscriptionId === 'I-PENDING-123',
  'pending PayPal activation should store the subscription id for retry',
);
assert(
  pendingStoredPayload.pendingPayPalActivation.expiresAt === pendingNow + 24 * 60 * 60,
  'pending PayPal activation should default to 24 hours',
);

pendingFetchCalls = 0;
const pendingStatus = await pendingManager.getStatus();
assert(pendingStatus.active === false, 'pending PayPal activation should not unlock license status');
assert(pendingStatus.provisional === true, 'pending status should remain visibly provisional');

const pendingToken = await pendingManager.getToken();
assert(
  pendingToken === null,
  'pending PayPal activation should not produce a backend session token before server verification',
);
assert(
  pendingFetchCalls === 0,
  'pending PayPal activation should not retry the license server during normal status/token checks',
);

const finalizedToken = signToken(keyPair.secretKey, {
  lic: 'LIC-PENDING-FINAL',
  plan: 'premium-desktop-monthly',
  kind: 'subscription',
  device: 'device-pending',
  iat: pendingNow,
  verified_at: pendingNow,
  requires_entitlement_refresh: true,
  next_verify_at: pendingNow + 7 * 24 * 60 * 60,
  exp: pendingNow + 9 * 24 * 60 * 60,
});
global.fetch = async (url, options) => {
  capturedUrl = new URL(String(url));
  capturedOptions = options;
  return {
    ok: true,
    json: async () => ({
      token: finalizedToken,
      licenseKey: 'LIC-PENDING-FINAL',
      status: { active: true, plan: 'premium-desktop-monthly', kind: 'subscription' },
    }),
  };
};

const verifyPendingResult = await pendingManager.verifyOnline();
const verifyPendingBody = JSON.parse(capturedOptions.body);
assert(verifyPendingResult.ok === true, 'Verify Now should finalize a pending PayPal activation');
assert(
  capturedUrl.pathname === '/license/activate-paypal',
  'Verify Now should use the PayPal activation endpoint for pending PayPal activations',
);
assert(
  verifyPendingBody.subscriptionId === 'I-PENDING-123',
  'Verify Now should retry the stored PayPal subscription id',
);
assert(
  pendingStoredPayload.token === finalizedToken,
  'Verify Now should replace the pending activation with the signed license token',
);
assert(
  !Object.hasOwn(verifyPendingResult.result, 'licenseKey'),
  'Verify Now must not expose the canonical license key',
);

const purchaseToken = signToken(keyPair.secretKey, {
  lic: 'LIC-WEBSITE-250',
  plan: 'premium-desktop-lifetime',
  kind: 'perpetual',
  device: 'device-purchase',
  iat: pendingNow,
  verified_at: pendingNow,
  requires_entitlement_refresh: false,
  offline_capable: true,
});
let purchaseStoredPayload;
global.fetch = async (url, options) => {
  capturedUrl = new URL(String(url));
  capturedOptions = options;
  return {
    ok: true,
    json: async () => ({
      token: purchaseToken,
      licenseKey: 'LIC-WEBSITE-250',
      status: { active: true, plan: 'premium-desktop-lifetime', kind: 'perpetual' },
    }),
  };
};
const purchaseManager = new LicenseManager(
  { getPath: () => process.cwd(), isPackaged: true },
  { serverUrl: 'https://license.example.test', publicKeyB64: Buffer.from(keyPair.publicKey).toString('base64') },
);
purchaseManager.getDeviceId = async () => 'device-purchase';
purchaseManager.writeStored = async (payload) => {
  purchaseStoredPayload = payload;
  return true;
};
purchaseManager.getStatus = async () => ({ active: true, plan: 'premium-desktop-lifetime' });

const purchaseResult = await purchaseManager.activatePayPalPurchase({
  paypalId: 'CAPTURE-250',
  email: 'buyer@example.com',
});
const purchaseBody = JSON.parse(capturedOptions.body);
assert(purchaseResult.ok === true, 'PayPal website purchase activation should succeed');
assert(
  !Object.hasOwn(purchaseResult, 'licenseKey'),
  'PayPal website activation must not expose the canonical license key',
);
assert(
  capturedUrl.pathname === '/license/activate-paypal-purchase',
  'PayPal website purchase activation should use the generic purchase endpoint',
);
assert(purchaseBody.paypalId === 'CAPTURE-250', 'PayPal website purchase activation should send the purchase id');
assert(purchaseBody.deviceId === 'device-purchase', 'PayPal website purchase activation should bind this device');
assert(purchaseStoredPayload.token === purchaseToken, 'PayPal website purchase activation should persist the signed token');

const expiredManager = new LicenseManager(
  { getPath: () => process.cwd(), isPackaged: true },
  { serverUrl: 'https://license.example.test' },
);
expiredManager.getDeviceId = async () => 'device-expired';
expiredManager.readStored = async () => ({
  pendingPayPalActivation: {
    subscriptionId: 'I-EXPIRED-123',
    plan: 'premium-desktop-monthly',
    createdAt: pendingNow,
    expiresAt: pendingNow + 24 * 60 * 60,
  },
});
expiredManager.clearStored = async () => {};

Date.now = () => (pendingNow + 24 * 60 * 60 + 1) * 1000;
const expiredStatus = await expiredManager.getStatus();
assert(expiredStatus.active === false, 'expired pending PayPal activation should stay locked');

global.fetch = originalFetch;
Date.now = originalDateNow;

console.log('licenseManagerPayPalActivation tests passed');
