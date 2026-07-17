import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const {
  PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
  PRODUCTION_LICENSE_SERVER_ORIGIN,
  validatePackagedLicenseConfig,
} = require('../main/security-policy');

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const configPath = path.resolve(scriptDir, '..', 'license.config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const propertyNames = Object.keys(config).sort();
if (
  propertyNames.length !== 2 ||
  propertyNames[0] !== 'publicKeyB64' ||
  propertyNames[1] !== 'serverUrl'
) {
  throw new Error('Production license config must contain only publicKeyB64 and serverUrl');
}

validatePackagedLicenseConfig(config, {
  expectedPublicKeySha256: PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
  expectedServerOrigin: PRODUCTION_LICENSE_SERVER_ORIGIN,
});

console.log('[license-config] Production origin and Ed25519 trust root verified.');
