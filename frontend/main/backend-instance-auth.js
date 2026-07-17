const crypto = require('crypto');

const INSTANCE_SECRET_ENV = 'VOX_STELLA_BACKEND_INSTANCE_SECRET_B64';
const INSTANCE_CHALLENGE_HEADER = 'X-VoxStella-Instance-Challenge';
const INSTANCE_PROOF_HEADER = 'X-VoxStella-Instance-Proof';

function createBackendInstanceSecret() {
  return crypto.randomBytes(32).toString('base64');
}

function createBackendInstanceChallenge() {
  return crypto.randomBytes(32).toString('base64url');
}

function decodeInstanceSecret(secretB64) {
  try {
    const secret = Buffer.from(String(secretB64 || ''), 'base64');
    return secret.length === 32 ? secret : null;
  } catch (_) {
    return null;
  }
}

function createBackendInstanceProof(secretB64, challenge, pathname) {
  const secret = decodeInstanceSecret(secretB64);
  const normalizedChallenge = String(challenge || '');
  const normalizedPathname = String(pathname || '');
  if (
    !secret ||
    !/^[A-Za-z0-9_-]{43}$/.test(normalizedChallenge) ||
    !normalizedPathname.startsWith('/')
  ) {
    return null;
  }
  return crypto
    .createHmac('sha256', secret)
    .update(`${normalizedChallenge}\n${normalizedPathname}`, 'utf8')
    .digest('hex');
}

function verifyBackendInstanceProof(secretB64, challenge, pathname, receivedProof) {
  const expected = createBackendInstanceProof(secretB64, challenge, pathname);
  const received = String(receivedProof || '').trim().toLowerCase();
  if (!expected || !/^[0-9a-f]{64}$/.test(received)) return false;
  return crypto.timingSafeEqual(Buffer.from(expected, 'hex'), Buffer.from(received, 'hex'));
}

module.exports = {
  INSTANCE_CHALLENGE_HEADER,
  INSTANCE_PROOF_HEADER,
  INSTANCE_SECRET_ENV,
  createBackendInstanceChallenge,
  createBackendInstanceProof,
  createBackendInstanceSecret,
  verifyBackendInstanceProof,
};
