const net = require('net');

const DEFAULT_BACKEND_PORT = 52525;

function parsePort(value) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) return null;
  if (parsed <= 0 || parsed > 65535) return null;
  return parsed;
}

function normalizePort(value, fallback = DEFAULT_BACKEND_PORT) {
  return parsePort(value) ?? fallback;
}

function createApiBaseUrl(port) {
  const normalizedPort = normalizePort(port);
  return `http://127.0.0.1:${normalizedPort}`;
}

function buildBackendLocalOrigins(port) {
  const normalizedPort = normalizePort(port);
  return new Set([
    `http://127.0.0.1:${normalizedPort}`,
    `http://localhost:${normalizedPort}`,
  ]);
}

function buildAppOrigins(port) {
  return new Set([
    'http://localhost:3000',
    'http://localhost:5173',
    ...buildBackendLocalOrigins(port),
  ]);
}

function findAvailablePort({ host = '127.0.0.1', preferredPort = 0 } = {}) {
  const desiredPort = parsePort(preferredPort) ?? 0;
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    const finalize = (error, port) => {
      try {
        server.close(() => {
          if (error) {
            reject(error);
            return;
          }
          resolve(port);
        });
      } catch (closeError) {
        if (error) {
          reject(error);
          return;
        }
        reject(closeError);
      }
    };

    server.once('error', (error) => {
      if (desiredPort > 0 && (error?.code === 'EADDRINUSE' || error?.code === 'EACCES')) {
        server.removeAllListeners('error');
        findAvailablePort({ host, preferredPort: 0 }).then(resolve, reject);
        return;
      }
      reject(error);
    });

    server.listen({ host, port: desiredPort, exclusive: true }, () => {
      const address = server.address();
      const resolvedPort = typeof address === 'object' && address ? address.port : desiredPort;
      finalize(null, resolvedPort);
    });
  });
}

async function resolveBackendPort({ appIsPackaged, configuredPort, host = '127.0.0.1' } = {}) {
  const explicitPort = parsePort(configuredPort);
  if (explicitPort) {
    return explicitPort;
  }
  if (!appIsPackaged) {
    return DEFAULT_BACKEND_PORT;
  }
  return findAvailablePort({ host, preferredPort: 0 });
}

module.exports = {
  DEFAULT_BACKEND_PORT,
  buildAppOrigins,
  buildBackendLocalOrigins,
  createApiBaseUrl,
  findAvailablePort,
  normalizePort,
  parsePort,
  resolveBackendPort,
};
