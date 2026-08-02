#!/usr/bin/env node
/*
 * Console-side stdio bridge for packaged Electron on Windows.
 *
 * Electron's GUI-subsystem executable does not reliably retain stdin when an
 * MCP host launches it directly. The same signed executable can run this file
 * as Node via ELECTRON_RUN_AS_NODE=1, then proxy stdio to a licensed hidden
 * Electron broker over an authenticated, per-process named pipe.
 */
const crypto = require('node:crypto');
const net = require('node:net');
const { spawn } = require('node:child_process');


const HANDSHAKE_PROTOCOL = 'vox-stella-mcp-bridge-v1';
// Packaged backend startup intentionally permits three 45-second readiness
// attempts. Keep the console bridge alive long enough for that retry contract,
// plus license initialization and the final named-pipe connection.
const DEFAULT_CONNECT_TIMEOUT_MS = 180000;
const configuredConnectTimeoutMs = Number(process.env.VOX_STELLA_MCP_CONNECT_TIMEOUT_MS);
const CONNECT_TIMEOUT_MS = Number.isFinite(configuredConnectTimeoutMs) && configuredConnectTimeoutMs >= 60000
  ? Math.floor(configuredConnectTimeoutMs)
  : DEFAULT_CONNECT_TIMEOUT_MS;
const MAX_HANDSHAKE_BYTES = 4096;


function argumentValue(name) {
  const prefix = `--${name}=`;
  const entry = process.argv.find((value) => value.startsWith(prefix));
  return entry ? entry.slice(prefix.length) : null;
}


function bridgeError(message) {
  process.stderr.write(`[vox-stella-mcp] ${message}\n`);
}


function main() {
  if (process.platform !== 'win32') {
    bridgeError('The packaged console bridge is currently required only on Windows.');
    process.exitCode = 1;
    return;
  }
  const targetExecutable = argumentValue('target-exe') || process.execPath;
  const targetApp = argumentValue('target-app');
  const secret = crypto.randomBytes(32).toString('hex');
  const pipeName = `\\\\.\\pipe\\vox-stella-mcp-${process.pid}-${crypto.randomBytes(12).toString('hex')}`;
  let child = null;
  let connected = false;
  let shuttingDown = false;

  const server = net.createServer((socket) => {
    if (connected) {
      socket.destroy();
      return;
    }
    let handshakeBuffer = Buffer.alloc(0);
    const failHandshake = (message) => {
      bridgeError(message);
      socket.destroy();
      shutdown(1);
    };
    const onHandshakeData = (chunk) => {
      handshakeBuffer = Buffer.concat([handshakeBuffer, chunk]);
      if (handshakeBuffer.length > MAX_HANDSHAKE_BYTES) {
        failHandshake('Broker handshake exceeded its size limit.');
        return;
      }
      const newlineIndex = handshakeBuffer.indexOf(0x0a);
      if (newlineIndex < 0) return;
      const line = handshakeBuffer.subarray(0, newlineIndex).toString('utf8');
      const remainder = handshakeBuffer.subarray(newlineIndex + 1);
      let handshake;
      try {
        handshake = JSON.parse(line);
      } catch (_) {
        failHandshake('Broker handshake was invalid.');
        return;
      }
      const suppliedSecret = Buffer.from(String(handshake?.secret || ''), 'utf8');
      const expectedSecret = Buffer.from(secret, 'utf8');
      if (
        handshake?.protocol !== HANDSHAKE_PROTOCOL ||
        suppliedSecret.length !== expectedSecret.length ||
        !crypto.timingSafeEqual(suppliedSecret, expectedSecret)
      ) {
        failHandshake('Broker authentication failed.');
        return;
      }
      connected = true;
      clearTimeout(connectTimer);
      socket.off('data', onHandshakeData);
      server.close();
      if (remainder.length) socket.unshift(remainder);
      socket.on('error', (error) => {
        bridgeError(`Broker pipe failed: ${String(error?.message || error)}`);
      });
      socket.on('close', () => shutdown(process.exitCode || 0));
      process.stdin.on('error', () => socket.destroy());
      process.stdout.on('error', () => socket.destroy());
      process.stdin.pipe(socket);
      socket.pipe(process.stdout);
    };
    socket.on('data', onHandshakeData);
    socket.on('error', (error) => failHandshake(`Broker pipe failed: ${String(error?.message || error)}`));
  });

  const shutdown = (exitCode) => {
    if (shuttingDown) return;
    shuttingDown = true;
    process.exitCode = exitCode;
    try { server.close(); } catch (_) {}
    try {
      if (child && child.exitCode == null && child.signalCode == null) child.kill('SIGTERM');
    } catch (_) {}
  };

  const connectTimer = setTimeout(() => {
    bridgeError('Timed out waiting for the licensed Electron broker.');
    shutdown(1);
  }, CONNECT_TIMEOUT_MS);

  server.on('error', (error) => {
    clearTimeout(connectTimer);
    bridgeError(`Unable to create the private MCP pipe: ${String(error?.message || error)}`);
    shutdown(1);
  });
  server.listen(pipeName, () => {
    const env = { ...process.env };
    delete env.ELECTRON_RUN_AS_NODE;
    env.VOX_STELLA_MCP_PIPE_B64 = Buffer.from(pipeName, 'utf8').toString('base64');
    env.VOX_STELLA_MCP_BRIDGE_SECRET = secret;
    const brokerArgs = [
      ...(targetApp ? [targetApp] : []),
      '--mcp-broker',
    ];
    child = spawn(targetExecutable, brokerArgs, {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      detached: false,
    });
    child.stdout.on('data', (chunk) => process.stderr.write(chunk));
    child.stderr.on('data', (chunk) => process.stderr.write(chunk));
    child.on('error', (error) => {
      bridgeError(`Unable to start Vox Stella: ${String(error?.message || error)}`);
      shutdown(1);
    });
    child.on('exit', (code) => {
      if (!connected && code !== 0) bridgeError(`Vox Stella broker exited with code ${code}.`);
      shutdown(Number.isInteger(code) ? code : (process.exitCode || 0));
    });
  });

  process.once('SIGINT', () => shutdown(130));
  process.once('SIGTERM', () => shutdown(143));
  process.once('exit', () => {
    try {
      if (child && child.exitCode == null && child.signalCode == null) child.kill('SIGTERM');
    } catch (_) {}
  });
}


main();
