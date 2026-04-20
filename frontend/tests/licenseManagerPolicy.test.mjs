import nacl from 'tweetnacl';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

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

const { __testing } = require('../main/license.js');

assert(
  __testing.licenseRequiresEntitlementRefresh({ plan: 'lifetime', kind: 'subscription' }) === true,
  'explicit subscription kind should override legacy perpetual plan names'
);

assert(
  __testing.licenseRequiresEntitlementRefresh({ plan: 'pro', kind: 'perpetual' }) === false,
  'explicit perpetual kind should allow offline use even when the plan name is generic'
);

const perpetualToken = signToken(keyPair.secretKey, {
  lic: 'LIC-PERP-1',
  plan: 'pro',
  kind: 'perpetual',
  device: 'device-1',
  iat: 1700000000,
  verified_at: 1700000000,
  requires_entitlement_refresh: false,
  offline_capable: true,
});

const perpetualPayload = __testing.verifySignedToken(perpetualToken);
assert(perpetualPayload.kind === 'perpetual', 'perpetual tokens should validate without refresh metadata');

const staleSubscriptionToken = signToken(keyPair.secretKey, {
  lic: 'LIC-SUB-1',
  plan: 'lifetime',
  kind: 'subscription',
  device: 'device-1',
  iat: 1700000000,
  verified_at: 1700000000,
  requires_entitlement_refresh: true,
  next_verify_at: 1,
});

let staleRejected = false;
try {
  __testing.verifySignedToken(staleSubscriptionToken);
} catch (err) {
  staleRejected = String(err?.message || '').toLowerCase().includes('refresh required');
}
assert(staleRejected, 'stale subscription tokens should be rejected even with legacy perpetual plan names');

console.log('licenseManagerPolicy tests passed');
