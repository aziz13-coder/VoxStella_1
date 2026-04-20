const net = require('net');
const {
  DEFAULT_BACKEND_PORT,
  buildAppOrigins,
  buildBackendLocalOrigins,
  createApiBaseUrl,
  findAvailablePort,
  normalizePort,
  parsePort,
  resolveBackendPort,
} = require('../main/backend-port');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => {
      server.removeListener('error', reject);
      resolve();
    });
  });
}

function close(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

(async () => {
  assert(parsePort('52525') === 52525, 'parsePort should accept a valid integer string');
  assert(parsePort('0') === null, 'parsePort should reject 0');
  assert(parsePort('70000') === null, 'parsePort should reject out-of-range ports');
  assert(normalizePort(undefined) === DEFAULT_BACKEND_PORT, 'normalizePort should fall back to the default port');
  assert(createApiBaseUrl(61111) === 'http://127.0.0.1:61111', 'createApiBaseUrl should build the loopback URL');

  const localOrigins = buildBackendLocalOrigins(61111);
  assert(localOrigins.has('http://127.0.0.1:61111'), 'loopback origin should be whitelisted');
  assert(localOrigins.has('http://localhost:61111'), 'localhost origin should be whitelisted');

  const appOrigins = buildAppOrigins(61111);
  assert(appOrigins.has('http://localhost:3000'), 'vite dev origin should remain whitelisted');
  assert(appOrigins.has('http://127.0.0.1:61111'), 'selected backend origin should be whitelisted');

  const devPort = await resolveBackendPort({ appIsPackaged: false });
  assert(devPort === DEFAULT_BACKEND_PORT, 'development runtime should keep the fixed backend port');

  const explicitPort = await resolveBackendPort({ appIsPackaged: true, configuredPort: '61234' });
  assert(explicitPort === 61234, 'explicit HORARY_PORT should be respected in packaged mode');

  const occupied = net.createServer();
  await listen(occupied, DEFAULT_BACKEND_PORT);
  try {
    const fallbackPort = await findAvailablePort({ preferredPort: DEFAULT_BACKEND_PORT });
    assert(
      Number.isInteger(fallbackPort) && fallbackPort > 0 && fallbackPort !== DEFAULT_BACKEND_PORT,
      'findAvailablePort should fall back when the preferred port is busy',
    );

    const packagedPort = await resolveBackendPort({ appIsPackaged: true });
    assert(
      Number.isInteger(packagedPort) && packagedPort > 0 && packagedPort !== DEFAULT_BACKEND_PORT,
      'packaged runtime should choose an isolated backend port instead of the fixed dev port',
    );
  } finally {
    await close(occupied);
  }

  console.log('backendPort tests passed');
})().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});
