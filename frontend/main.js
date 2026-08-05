// Electron main process: creates window, starts backend, injects API base, and cleans up.
const MCP_BROKER_MODE = process.argv.includes('--mcp-broker');
const MCP_MODE = MCP_BROKER_MODE || process.argv.includes('--mcp');
if (MCP_MODE) {
  // MCP stdio reserves stdout exclusively for protocol messages.
  const writeMcpDiagnostic = console.error.bind(console);
  console.log = writeMcpDiagnostic;
  console.info = writeMcpDiagnostic;
  console.debug = writeMcpDiagnostic;
}
const { app, BrowserWindow, clipboard, ipcMain, dialog, shell, session } = require('electron');
const path = require('path');
const crypto = require('crypto');
const net = require('net');
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const {
  DEFAULT_BACKEND_PORT,
  createApiBaseUrl,
  normalizePort,
  resolveBackendPort,
} = require('./main/backend-port');
const { requestJsonWithDeadline } = require('./main/backend-http');
const { configureRuntimeEnv } = require('./main/runtime-env');
const {
  PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
  PRODUCTION_LICENSE_SERVER_ORIGIN,
  buildPayPalCheckoutUrl,
  isAllowedExternalUrl,
  isAllowedRendererUrl,
  validatePackagedLicenseConfig,
  validateReportPayload,
} = require('./main/security-policy');
const {
  validatePackagedBackendSmoke,
  writeSmokeResultFile,
} = require('./main/smoke-contract');
const {
  INSTANCE_CHALLENGE_HEADER,
  INSTANCE_PROOF_HEADER,
  INSTANCE_SECRET_ENV,
  createBackendInstanceChallenge,
  createBackendInstanceSecret,
  verifyBackendInstanceProof,
} = require('./main/backend-instance-auth');
const { createBackendParentState } = require('./main/backend-parent-state');
const {
  buildMcpSetupStatus,
  resolveMcpLauncherPath,
} = require('./main/mcp/setup');
const {
  acquireSingleInstanceLock,
  focusWindow,
} = require('./main/single-instance');
// Optional modules (exist if installed)
let initAutoUpdater; try { ({ initAutoUpdater } = require('./main/updater')); } catch (_) {}
let LicenseManager; try { ({ LicenseManager } = require('./main/license')); } catch (_) {}

const CONFIGURED_BACKEND_PORT = process.env.HORARY_PORT;
let PORT = normalizePort(CONFIGURED_BACKEND_PORT, DEFAULT_BACKEND_PORT);
let API_BASE_URL = createApiBaseUrl(PORT);
const OSM_TILE_HOST_SUFFIX = '.tile.openstreetmap.org';
const OSM_TILE_REFERER = 'https://voxstella.app/';
const PACKAGED_RENDERER_ENTRY = path.join(__dirname, 'dist', 'index.html');
const DEVELOPMENT_RENDERER_ORIGINS = ['http://localhost:5173'];
const SMOKE_TEST_MODE =
  process.argv.includes('--smoke-test') ||
  process.env.VOX_STELLA_SMOKE_TEST === '1';
const MAIN_LOG_MAX_BYTES = Math.max(
  1024 * 1024,
  Number(process.env.VOX_STELLA_MAIN_LOG_MAX_BYTES || 5 * 1024 * 1024),
);
const BACKEND_LOG_MAX_BYTES = Math.max(
  1024 * 1024,
  Number(process.env.VOX_STELLA_BACKEND_LOG_MAX_BYTES || 10 * 1024 * 1024),
);

function ensureLogDir(logDir) {
  if (!logDir) return false;
  try {
    if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
    return true;
  } catch (_) {
    return false;
  }
}

function rotateLogIfLarge(filePath, maxBytes) {
  if (!filePath || !Number.isFinite(maxBytes) || maxBytes <= 0) return;
  try {
    if (!fs.existsSync(filePath)) return;
    const stat = fs.statSync(filePath);
    if (!stat || stat.size < maxBytes) return;
    const rotatedPath = `${filePath}.1`;
    try {
      if (fs.existsSync(rotatedPath)) fs.unlinkSync(rotatedPath);
    } catch (_) {}
    fs.renameSync(filePath, rotatedPath);
  } catch (_) {}
}

function serializeLogArg(arg) {
  if (arg instanceof Error) return arg.stack || arg.message;
  if (typeof arg === 'string') return arg;
  try {
    return JSON.stringify(arg);
  } catch (_) {
    return String(arg);
  }
}

function formatLogLine(level, args) {
  const timestamp = new Date().toISOString();
  const message = (args || []).map(serializeLogArg).join(' ');
  return `[${timestamp}] [${String(level || 'log').toUpperCase()}] ${message}\n`;
}

function applyBackendPort(nextPort) {
  PORT = normalizePort(nextPort, DEFAULT_BACKEND_PORT);
  API_BASE_URL = createApiBaseUrl(PORT);
  process.env.HORARY_PORT = String(PORT);
  process.env.API_BASE_URL = API_BASE_URL;
}

function configureMapTileRequestHeaders() {
  const ses = session.defaultSession;
  if (!ses || typeof ses.webRequest?.onBeforeSendHeaders !== 'function') return;
  ses.webRequest.onBeforeSendHeaders(
    {
      urls: [
        'https://tile.openstreetmap.org/*',
        'https://*.tile.openstreetmap.org/*',
      ],
    },
    (details, callback) => {
      const headers = { ...(details.requestHeaders || {}) };
      let hostname = '';
      try {
        hostname = new URL(details.url).hostname.toLowerCase();
      } catch (_) {}
      const isOsmTileHost = hostname === 'tile.openstreetmap.org' || hostname.endsWith(OSM_TILE_HOST_SUFFIX);
      if (isOsmTileHost) {
        headers.Referer = OSM_TILE_REFERER;
        headers['User-Agent'] = headers['User-Agent'] || `VoxStella/${app.getVersion()} (+https://voxstella.app/)`;
      }
      callback({ cancel: false, requestHeaders: headers });
    },
  );
}

function denySessionPermissions(targetSession, { allowTrustedClipboardWrite = false } = {}) {
  if (!targetSession) return;
  const canWriteClipboard = (webContents, permission) => (
    allowTrustedClipboardWrite &&
    permission === 'clipboard-sanitized-write' &&
    webContents === mainWindow?.webContents &&
    !mainWindow?.isDestroyed() &&
    isAllowedAppNavigation(webContents.getURL?.() || '')
  );
  try {
    targetSession.setPermissionCheckHandler?.((webContents, permission) => (
      canWriteClipboard(webContents, permission)
    ));
  } catch (_) {}
  try {
    targetSession.setPermissionRequestHandler?.((webContents, permission, callback) => {
      callback(canWriteClipboard(webContents, permission));
    });
  } catch (_) {}
  try {
    targetSession.setDevicePermissionHandler?.(() => false);
  } catch (_) {}
  try {
    targetSession.setUSBProtectedClassesHandler?.(() => []);
  } catch (_) {}
}

function configureRendererSessionSecurity() {
  const ses = session.defaultSession;
  denySessionPermissions(ses, { allowTrustedClipboardWrite: true });
}

let mainWindow = null;
let backendProc = null;
let closed = false;
let backendKillStarted = false;
let licenseManager = null;
let backendLogDir = null;
let mainLogPath = null;
let backendRestartAttempts = 0;
let backendRestartTimer = null;
let backendParentState = null;
let backendHeartbeatTimer = null;
let ipcHandlersRegistered = false;
let backendLicenseSessionSecretB64 = null;
let backendInstanceSecretB64 = null;
let packagedLicensePublicKeySha256 = null;
let backendStatus = 'checking';
let backendStartupDeadlineMs = 0;
let backendStatusPollTimer = null;
let backendStatusProbePromise = null;
let backendConsecutiveProbeFailures = 0;
let backendRecoveryInProgress = false;
let fatalExitStarted = false;
let initialBackendReadinessPending = false;
let secondInstanceFocusPending = false;
const MAX_BACKEND_RESTARTS = (() => {
  const raw = Number(process.env.VOX_STELLA_BACKEND_RESTARTS || 3);
  return Number.isFinite(raw) && raw >= 0 ? Math.floor(raw) : 3;
})();
const DEFAULT_BACKEND_STATUS_BOOT_GRACE_MS = app.isPackaged ? 45000 : 20000;
const BACKEND_STATUS_BOOT_GRACE_MS = Math.max(
  5000,
  Number(process.env.VOX_STELLA_BACKEND_BOOT_GRACE_MS || DEFAULT_BACKEND_STATUS_BOOT_GRACE_MS),
);
const DEFAULT_BACKEND_STATUS_FAILURE_THRESHOLD = app.isPackaged ? 3 : 1;
const BACKEND_STATUS_FAILURE_THRESHOLD = Math.max(
  1,
  Number(process.env.VOX_STELLA_BACKEND_STATUS_FAILURE_THRESHOLD || DEFAULT_BACKEND_STATUS_FAILURE_THRESHOLD),
);
const BACKEND_STATUS_POLL_MS = Math.max(1000, Number(process.env.VOX_STELLA_BACKEND_STATUS_POLL_MS || 2500));
const DEFAULT_BACKEND_STATUS_PING_TIMEOUT_MS = app.isPackaged ? 5000 : 1500;
const BACKEND_STATUS_PING_TIMEOUT_MS = Math.max(
  1000,
  Number(process.env.VOX_STELLA_BACKEND_STATUS_PING_TIMEOUT_MS || DEFAULT_BACKEND_STATUS_PING_TIMEOUT_MS),
);

if (SMOKE_TEST_MODE) {
  app.setPath(
    'userData',
    path.join(app.getPath('temp'), `VoxStella-smoke-${process.pid}`),
  );
}

const hasSingleInstanceLock = MCP_MODE
  ? true
  : acquireSingleInstanceLock(
    app,
    () => mainWindow,
    {
      onWindowUnavailable: () => {
        if (closed || backendKillStarted) return;
        secondInstanceFocusPending = true;
        if (ipcHandlersRegistered && BrowserWindow.getAllWindows().length === 0) {
          void createWindow();
        }
      },
    },
  );
if (!hasSingleInstanceLock) {
  closed = true;
  app.quit();
}

function configureMainFileLogging(logDir) {
  if (mainLogPath || !ensureLogDir(logDir)) return;
  mainLogPath = path.join(logDir, 'main.log');
  rotateLogIfLarge(mainLogPath, MAIN_LOG_MAX_BYTES);
  const originalConsole = {
    log: console.log.bind(console),
    warn: console.warn.bind(console),
    error: console.error.bind(console),
  };
  const writeLine = (level, args) => {
    try {
      fs.appendFileSync(mainLogPath, formatLogLine(level, args), 'utf8');
    } catch (_) {}
  };
  console.log = (...args) => {
    originalConsole.log(...args);
    writeLine('log', args);
  };
  console.warn = (...args) => {
    originalConsole.warn(...args);
    writeLine('warn', args);
  };
  console.error = (...args) => {
    originalConsole.error(...args);
    writeLine('error', args);
  };
  console.log(`[diagnostics] main log: ${mainLogPath}`);
}

function getDiagnosticsLogPaths() {
  let logDir = backendLogDir;
  if (!logDir) {
    try {
      logDir = path.join(app.getPath('userData'), 'logs');
    } catch (_) {}
  }
  return {
    logDir,
    mainLogPath: mainLogPath || (logDir ? path.join(logDir, 'main.log') : null),
    backendLogPath: logDir ? path.join(logDir, 'backend.log') : null,
  };
}

function broadcastBackendStatus() {
  try {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend:status', { status: backendStatus });
    }
  } catch (_) {}
}

function setBackendStatus(nextStatus, { force = false } = {}) {
  const normalized = typeof nextStatus === 'string' && nextStatus.trim() ? nextStatus.trim() : 'checking';
  if (!force && backendStatus === normalized) return;
  backendStatus = normalized;
  broadcastBackendStatus();
}

function markBackendStarting(graceMs = BACKEND_STATUS_BOOT_GRACE_MS) {
  backendStartupDeadlineMs = Date.now() + graceMs;
  backendConsecutiveProbeFailures = 0;
  setBackendStatus('checking', { force: true });
}

function isWithinBackendStartupWindow() {
  return Date.now() < backendStartupDeadlineMs;
}

function getBackendStatusAfterProbeFailure() {
  if (isWithinBackendStartupWindow()) {
    return 'checking';
  }
  if (backendConsecutiveProbeFailures < BACKEND_STATUS_FAILURE_THRESHOLD) {
    return backendStatus === 'connected' ? 'connected' : 'checking';
  }
  return 'offline';
}

function isReachableVersionPayload(parsed) {
  const appVersion = parsed?.app_version;
  const apiVersion = parsed?.api_version;
  return (
    typeof appVersion === 'string' &&
    appVersion.trim() &&
    typeof apiVersion === 'string' &&
    apiVersion.trim()
  );
}

async function requestBackendJson(pathname, timeoutMs = BACKEND_STATUS_PING_TIMEOUT_MS) {
  const requestUrl = new URL(`${API_BASE_URL}${pathname}`);
  const proofPathname = requestUrl.pathname;
  const challenge = app.isPackaged ? createBackendInstanceChallenge() : null;
  const response = await requestJsonWithDeadline(requestUrl, {
    timeoutMs,
    headers: challenge ? { [INSTANCE_CHALLENGE_HEADER]: challenge } : {},
  });
  if (
    response.ok &&
    app.isPackaged &&
    !verifyBackendInstanceProof(
      backendInstanceSecretB64,
      challenge,
      proofPathname,
      response.headers?.[String(INSTANCE_PROOF_HEADER).toLowerCase()],
    )
  ) {
    return {
      ok: false,
      statusCode: response.statusCode,
      error: 'invalid_instance_proof',
    };
  }
  return response;
}

async function probeBackendReachabilityOnce(timeoutMs = BACKEND_STATUS_PING_TIMEOUT_MS) {
  const response = await requestBackendJson('/api/version', timeoutMs);
  return Boolean(response.ok && isReachableVersionPayload(response.payload));
}

async function refreshBackendStatus(options = {}) {
  const {
    timeoutMs = BACKEND_STATUS_PING_TIMEOUT_MS,
    forceBroadcast = false,
  } = options;
  if (backendStatusProbePromise) return backendStatusProbePromise;
  backendStatusProbePromise = (async () => {
    const reachable = await probeBackendReachabilityOnce(timeoutMs);
    if (reachable) {
      backendConsecutiveProbeFailures = 0;
    } else {
      backendConsecutiveProbeFailures += 1;
    }
    const nextStatus = reachable ? 'connected' : getBackendStatusAfterProbeFailure();
    setBackendStatus(nextStatus, { force: forceBroadcast });
    if (
      nextStatus === 'offline' &&
      app.isPackaged &&
      !closed &&
      !backendKillStarted &&
      backendProc &&
      !backendProc.killed
    ) {
      void recoverUnresponsiveBackend('health-probe-failures');
    }
    return nextStatus;
  })();
  try {
    return await backendStatusProbePromise;
  } finally {
    backendStatusProbePromise = null;
  }
}

function startBackendStatusMonitor() {
  if (backendStatusPollTimer) return;
  const tick = () => {
    void refreshBackendStatus();
  };
  tick();
  backendStatusPollTimer = setInterval(tick, BACKEND_STATUS_POLL_MS);
  if (typeof backendStatusPollTimer.unref === 'function') {
    backendStatusPollTimer.unref();
  }
}

function stopBackendStatusMonitor() {
  if (backendStatusPollTimer) {
    clearInterval(backendStatusPollTimer);
    backendStatusPollTimer = null;
  }
}

function clearBackendRestartTimer() {
  if (backendRestartTimer) {
    clearTimeout(backendRestartTimer);
    backendRestartTimer = null;
  }
}

function ensureBackendParentStateFile(logDir) {
  if (backendParentState) return backendParentState.stateFile;
  const baseDir = logDir || app.getPath('userData');
  backendParentState = createBackendParentState(baseDir, { pid: process.pid });
  return backendParentState.stateFile;
}

function writeBackendParentState() {
  const state = backendParentState;
  if (!state) return;
  try {
    state.write();
  } catch (_) {}
}

function startBackendHeartbeat(logDir) {
  try {
    const stateFile = ensureBackendParentStateFile(logDir);
    backendParentState.write();
    if (backendHeartbeatTimer) clearInterval(backendHeartbeatTimer);
    backendHeartbeatTimer = setInterval(writeBackendParentState, 1000);
    if (typeof backendHeartbeatTimer.unref === 'function') {
      backendHeartbeatTimer.unref();
    }
    return stateFile;
  } catch (error) {
    if (backendParentState) {
      try { backendParentState.cleanup(); } catch (_) {}
      backendParentState = null;
    }
    console.warn('Backend parent heartbeat unavailable; using PID watchdog only:', error);
    return null;
  }
}

function stopBackendHeartbeat() {
  if (backendHeartbeatTimer) {
    clearInterval(backendHeartbeatTimer);
    backendHeartbeatTimer = null;
  }
  if (backendParentState) {
    const state = backendParentState;
    backendParentState = null;
    try { state.cleanup(); } catch (_) {}
  }
}

function isAllowedAppNavigation(rawUrl) {
  return isAllowedRendererUrl(rawUrl, {
    isPackaged: app.isPackaged,
    packagedEntryPath: PACKAGED_RENDERER_ENTRY,
    developmentOrigins: DEVELOPMENT_RENDERER_ORIGINS,
  });
}

function loadLicenseConfig() {
  const candidates = [];
  try {
    if (process?.resourcesPath) {
      candidates.push(path.join(process.resourcesPath, 'license.config.json'));
    }
  } catch (_) {}
  candidates.push(path.join(__dirname, 'license.config.json'));
  candidates.push(path.join(__dirname, '..', 'license.config.json'));
  for (const cfgPath of candidates) {
    try {
      if (cfgPath && fs.existsSync(cfgPath)) {
        const parsed = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
        if (parsed && typeof parsed === 'object') return parsed;
      }
    } catch (err) {
      console.warn('Failed to read license config', cfgPath, err?.message || err);
    }
  }
  return {};
}

const RUNTIME_LICENSE_CONFIG = loadLicenseConfig();

function resolveBackendCommand() {
  // Prefer packaged runtime bundle under resources/backend/runtime.
  const candidates = [];
  const resources = process.resourcesPath || path.join(__dirname);
  const backendExecutableName = process.platform === 'win32' ? 'horary_backend.exe' : 'horary_backend';
  candidates.push(path.join(
    resources,
    'backend',
    'runtime',
    'horary_backend',
    backendExecutableName,
  ));
  // Backward compatibility for older packaged layouts.
  candidates.push(path.join(resources, 'backend', backendExecutableName));
  // Some workflows place exe directly in resources
  candidates.push(path.join(resources, backendExecutableName));
  // Dev fallback: python app.py from repo backend folder
  candidates.push(path.join(__dirname, '..', 'backend', 'app.py'));

  console.log('=== Backend Resolution Debug ===');
  console.log('process.resourcesPath:', process.resourcesPath);
  console.log('__dirname:', __dirname);
  console.log('resources path:', resources);
  console.log('Platform:', process.platform);
  console.log('Candidates to check:');
  candidates.forEach((c, i) => console.log(`  ${i + 1}. ${c}`));

  for (const p of candidates) {
    console.log(`Checking candidate: ${p}`);
    try {
      require('fs').accessSync(p);
      console.log(`✓ Found backend executable: ${p}`);
      if (p.endsWith('.py')) {
        const result = { cmd: process.platform === 'win32' ? 'python' : 'python3', args: [p], cwd: path.dirname(p) };
        console.log('Using Python:', result);
        return result;
      }
      const result = { cmd: p, args: [], cwd: path.dirname(p) };
      console.log('Using executable:', result);
      return result;
    } catch (e) { 
      console.log(`✗ Not found: ${p} (${e.message})`);
    }
  }
  console.log('No backend executable found in any candidate location');
  return null;
}

async function ensurePackagedLicenseSecurityContext() {
  if (!app.isPackaged) return;
  if (typeof LicenseManager !== 'function') {
    throw new Error('Packaged licensing module is unavailable');
  }
  const trustedConfig = validatePackagedLicenseConfig(RUNTIME_LICENSE_CONFIG, {
    expectedPublicKeySha256: PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
    expectedServerOrigin: PRODUCTION_LICENSE_SERVER_ORIGIN,
  });
  if (!licenseManager) {
    licenseManager = new LicenseManager(app, trustedConfig);
  }
  const managerConfig = validatePackagedLicenseConfig(
    {
      serverUrl: licenseManager.serverUrl,
      publicKeyB64: licenseManager.publicKeyB64,
    },
    {
      expectedPublicKeySha256: PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
      expectedServerOrigin: PRODUCTION_LICENSE_SERVER_ORIGIN,
    },
  );
  if (
    managerConfig.serverUrl !== trustedConfig.serverUrl ||
    managerConfig.publicKeyB64 !== trustedConfig.publicKeyB64
  ) {
    throw new Error('Packaged license manager configuration does not match the bundled trust root');
  }
  packagedLicensePublicKeySha256 = crypto
    .createHash('sha256')
    .update(Buffer.from(trustedConfig.publicKeyB64, 'base64'))
    .digest('hex');
  const deviceId = await licenseManager.getDeviceId().catch(() => null);
  if (typeof deviceId !== 'string' || deviceId.trim().length < 32) {
    throw new Error('Packaged device identity could not be derived');
  }
  process.env.VOX_STELLA_DEVICE_ID = deviceId.trim();
  if (!backendLicenseSessionSecretB64) {
    backendLicenseSessionSecretB64 = crypto.randomBytes(32).toString('base64');
  }
  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = backendLicenseSessionSecretB64;
}

async function ensureMcpLicenseSecurityContext() {
  if (typeof LicenseManager !== 'function') {
    throw new Error('Vox Stella licensing is unavailable');
  }
  if (app.isPackaged) {
    await ensurePackagedLicenseSecurityContext();
    return licenseManager;
  }
  if (!licenseManager) {
    licenseManager = new LicenseManager(app, RUNTIME_LICENSE_CONFIG);
  }
  const deviceId = await licenseManager.getDeviceId().catch(() => null);
  if (typeof deviceId !== 'string' || deviceId.trim().length < 32) {
    throw new Error('Vox Stella device identity could not be derived');
  }
  process.env.VOX_STELLA_DEVICE_ID = deviceId.trim();
  if (!backendLicenseSessionSecretB64) {
    backendLicenseSessionSecretB64 = crypto.randomBytes(32).toString('base64');
  }
  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = backendLicenseSessionSecretB64;
  return licenseManager;
}

async function startBackend(logDir) {
  console.log('=== Starting Backend ===');
  markBackendStarting();
  const resolved = resolveBackendCommand();
  if (!resolved) {
    if (app.isPackaged) {
      throw new Error('Packaged backend executable is missing');
    }
    console.warn('Backend executable not found. Assuming an external backend is running.');
    return null;
  }
  await ensurePackagedLicenseSecurityContext();
  const parentStateFile = startBackendHeartbeat(logDir);
  const env = { ...process.env, HORARY_PORT: String(PORT) };
  const captureBackendToFile = process.env.VOX_STELLA_CAPTURE_BACKEND_STDIO !== '0';
  env.VOX_STELLA_PARENT_PID = String(process.pid);
  env.VOX_STELLA_APP_VERSION = app.getVersion();
  if (parentStateFile) env.VOX_STELLA_PARENT_STATE_FILE = parentStateFile;
  // Never inherit license bypass flags unless explicitly enabled in dev.
  delete env.LICENSE_BYPASS;
  delete env.ALLOW_DEV_LICENSE_BYPASS;
  delete env.LICENSE_SERVER_URL;
  delete env.LICENSE_PUBLIC_KEY_B64;
  delete env[INSTANCE_SECRET_ENV];
  env.APP_IS_PACKAGED = app.isPackaged ? '1' : '0';
  if (app.isPackaged) {
    if (!backendInstanceSecretB64) {
      backendInstanceSecretB64 = createBackendInstanceSecret();
    }
    env[INSTANCE_SECRET_ENV] = backendInstanceSecretB64;
  }
  if (MCP_MODE && !app.isPackaged) {
    // Source-mode MCP must exercise the real license chain as well.
    env.ALLOW_DEV_LICENSE_BYPASS = '0';
    env.LICENSE_BYPASS = '0';
    env.VOX_STELLA_ENV = 'production';
  } else if (!app.isPackaged && process.env.ALLOW_DEV_LICENSE_BYPASS === '1') {
    env.ALLOW_DEV_LICENSE_BYPASS = '1';
  }
  if (app.isPackaged && RUNTIME_LICENSE_CONFIG.publicKeyB64) {
    env.LICENSE_PUBLIC_KEY_B64 = String(RUNTIME_LICENSE_CONFIG.publicKeyB64).trim();
  } else if (!app.isPackaged && process.env.LICENSE_PUBLIC_KEY_B64) {
    env.LICENSE_PUBLIC_KEY_B64 = String(process.env.LICENSE_PUBLIC_KEY_B64).trim();
  } else if (!env.LICENSE_PUBLIC_KEY_B64 && RUNTIME_LICENSE_CONFIG.publicKeyB64) {
    env.LICENSE_PUBLIC_KEY_B64 = String(RUNTIME_LICENSE_CONFIG.publicKeyB64).trim();
  }
  // Speed up research compile by default in packaged builds
  if (!process.env.RESEARCH_WORKERS) env.RESEARCH_WORKERS = '16';
  if (!process.env.RESEARCH_CHUNK) env.RESEARCH_CHUNK = '256';
  try {
    // Help backend find resources (traits catalog, etc.) in packaged builds
    if (resolved && resolved.cwd) {
      env.HORARY_BACKEND_DIR = resolved.cwd;
    }
  } catch (_) {}
  if (logDir) env.HORARY_LOG_DIR = logDir;
  if (!env.LICENSE_PUBLIC_KEY_B64) {
    console.warn('LICENSE_PUBLIC_KEY_B64 is not defined. Backend license checks will fail.');
  }
  const verboseBackendLogs = !app.isPackaged || process.env.VOX_STELLA_VERBOSE_BACKEND_LOGS === '1';
  console.log(`Starting backend: ${resolved.cmd} ${resolved.args.join(' ')} on ${API_BASE_URL}`);
  console.log(`Working directory: ${resolved.cwd}`);
  console.log(`Environment PORT: ${env.HORARY_PORT}`);
  
  try {
    const child = spawn(resolved.cmd, resolved.args, {
      cwd: resolved.cwd,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      detached: false,
    });
    
    console.log(`Backend process spawned with PID: ${child.pid}`);
    // Keep stdout/stderr drained and persist bounded diagnostics for installed builds.
    // Set VOX_STELLA_CAPTURE_BACKEND_STDIO=0 to disable this capture.
    try {
      let logStream = null;
      let logPath = null;
      if (captureBackendToFile) {
        if (logDir) ensureLogDir(logDir);
        logPath = logDir ? path.join(logDir, 'backend.log') : path.join(resolved.cwd, 'backend.log');
        rotateLogIfLarge(logPath, BACKEND_LOG_MAX_BYTES);
        logStream = fs.createWriteStream(logPath, { flags: 'a' });
      }
      
      child.stdout.on('data', (d) => {
        if (verboseBackendLogs) {
          console.log('Backend stdout:', d.toString().trim());
        }
        if (logStream) logStream.write(d);
      });
      child.stderr.on('data', (d) => {
        if (verboseBackendLogs) {
          console.log('Backend stderr:', d.toString().trim());
        }
        if (logStream) logStream.write(d);
      });
      child.on('exit', () => {
        if (logStream) logStream.end();
      });
      if (logPath) {
        console.log(`Backend logs: ${logPath}`);
      } else {
        console.log('Backend stdout/stderr capture to file disabled for this run');
      }
    } catch (e) {
      console.warn('Failed to initialize backend log stream:', e);
    }
    
    child.on('exit', (code, signal) => {
      console.log(`Backend exited: code=${code} signal=${signal}`);
      if (!closed && !backendKillStarted) {
        console.log(`Backend process terminated unexpectedly`);
        if (backendProc && backendProc.pid === child.pid) {
          backendProc = null;
          markBackendStarting();
          if (!initialBackendReadinessPending) {
            scheduleBackendRestart(`exit:${code ?? 'unknown'}`);
          }
        }
      }
    });
    
    child.on('error', (error) => {
      console.error('Backend process error:', error);
      if (!closed && !backendKillStarted) {
        if (backendProc && backendProc.pid === child.pid) {
          backendProc = null;
          markBackendStarting();
          if (!initialBackendReadinessPending) {
            scheduleBackendRestart('spawn-error');
          }
        }
      }
    });
    
    return child;
  } catch (error) {
    console.error('Failed to spawn backend process:', error);
    return null;
  }
}

function terminateBackendChild(child, { forceAfterMs = 2000 } = {}) {
  return new Promise((resolve) => {
    if (!child) {
      resolve();
      return;
    }
    let settled = false;
    let forceTimer = null;
    const finish = () => {
      if (settled) return;
      settled = true;
      if (forceTimer) clearTimeout(forceTimer);
      resolve();
    };
    try {
      child.once?.('exit', finish);
      child.once?.('error', finish);
    } catch (_) {}
    try {
      child.kill('SIGTERM');
    } catch (_) {
      finish();
      return;
    }
    if (settled) return;
    forceTimer = setTimeout(() => {
      try {
        if (process.platform === 'win32' && child.pid) {
          spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
            windowsHide: true,
            stdio: 'ignore',
          });
        } else {
          child.kill('SIGKILL');
        }
      } catch (_) {}
      finish();
    }, forceAfterMs);
    if (typeof forceTimer.unref === 'function') forceTimer.unref();
  });
}

async function recoverUnresponsiveBackend(reason = 'unresponsive') {
  if (
    backendRecoveryInProgress ||
    !app.isPackaged ||
    closed ||
    backendKillStarted ||
    backendRestartTimer
  ) {
    return;
  }
  const child = backendProc;
  if (!child) {
    scheduleBackendRestart(reason);
    return;
  }
  backendRecoveryInProgress = true;
  backendProc = null;
  markBackendStarting();
  console.warn(`[backend] terminating unresponsive process ${child.pid || 'unknown'} after ${reason}`);
  try {
    await terminateBackendChild(child);
  } finally {
    backendRecoveryInProgress = false;
  }
  scheduleBackendRestart(reason);
}

function scheduleBackendRestart(reason = 'unknown') {
  if (!app.isPackaged || closed || backendKillStarted) return;
  if (backendRestartTimer) return;
  if (backendRestartAttempts >= MAX_BACKEND_RESTARTS) {
    console.error(`[backend] restart limit reached (${MAX_BACKEND_RESTARTS}). Last reason: ${reason}`);
    setBackendStatus('offline', { force: true });
    return;
  }
  markBackendStarting();
  const nextAttempt = backendRestartAttempts + 1;
  const delayMs = Math.min(1000 * (2 ** (nextAttempt - 1)), 15000);
  backendRestartAttempts = nextAttempt;
  backendRestartTimer = setTimeout(async () => {
    backendRestartTimer = null;
    if (closed || backendKillStarted) return;
    console.warn(`[backend] attempting restart ${nextAttempt}/${MAX_BACKEND_RESTARTS} after ${reason}`);
    backendProc = await startBackend(backendLogDir);
    const ok = await waitForBackendReachability(12000);
    if (ok) {
      backendRestartAttempts = 0;
      setBackendStatus('connected', { force: true });
      console.log('[backend] restart successful');
      return;
    }
    console.warn('[backend] restart reachability check failed');
    if (!isWithinBackendStartupWindow()) {
      setBackendStatus('offline', { force: true });
    }
    const failedChild = backendProc;
    backendProc = null;
    await terminateBackendChild(failedChild);
    scheduleBackendRestart('restart-timeout');
  }, delayMs);
}

async function waitForBackendReachability(timeoutMs = 12000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() <= deadline) {
    if (await probeBackendReachabilityOnce(1500)) return true;
    if (app.isPackaged && initialBackendReadinessPending && !backendProc) return false;
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  return false;
}

function isTrustedIpcEvent(event) {
  try {
    const sender = event?.sender;
    const windowContents = mainWindow?.webContents;
    if (
      !sender ||
      !windowContents ||
      mainWindow.isDestroyed() ||
      sender !== windowContents ||
      sender.isDestroyed?.()
    ) {
      return false;
    }
    const senderFrame = event?.senderFrame;
    if (senderFrame?.parent) return false;
    const senderUrl = senderFrame?.url || sender.getURL?.() || '';
    return isAllowedAppNavigation(senderUrl);
  } catch (_) {
    return false;
  }
}

function registerTrustedIpcHandler(channel, handler) {
  ipcMain.handle(channel, async (event, ...args) => {
    if (!isTrustedIpcEvent(event)) {
      console.warn(`[ipc] rejected untrusted sender for ${channel}`);
      throw new Error('Unauthorized IPC sender');
    }
    return handler(event, ...args);
  });
}

async function getMcpSetupStatus() {
  const launcherPath = resolveMcpLauncherPath({
    appIsPackaged: app.isPackaged,
    executablePath: process.execPath,
    frontendRoot: __dirname,
  });
  const licenseStatus = licenseManager?.getStatus
    ? await licenseManager.getStatus().catch(() => ({ active: false }))
    : { active: !app.isPackaged };
  return buildMcpSetupStatus({
    appIsPackaged: app.isPackaged,
    appVersion: app.getVersion(),
    launcherExists: app.isPackaged && fs.existsSync(launcherPath),
    launcherPath,
    licenseActive: licenseStatus?.active === true,
    platform: process.platform,
  });
}

function registerCoreIpcHandlers() {
  if (ipcHandlersRegistered) return;
  ipcHandlersRegistered = true;

  // Initialize licensing IPC
  try {
    if (LicenseManager) {
      if (app.isPackaged) {
        if (!licenseManager) {
          licenseManager = new LicenseManager(app);
        }
        registerTrustedIpcHandler('license:get-status', async () => licenseManager.getStatus());
        registerTrustedIpcHandler('license:activate', async (_e, payload) => {
          const result = await licenseManager.activate(payload || {});
          return result;
        });
        registerTrustedIpcHandler('license:activate-paypal-subscription', async (_e, payload) => {
          const result = await licenseManager.activatePayPalSubscription(payload || {});
          return result;
        });
        registerTrustedIpcHandler('license:activate-paypal-purchase', async (_e, payload) => {
          const result = await licenseManager.activatePayPalPurchase(payload || {});
          return result;
        });
        registerTrustedIpcHandler('license:deactivate', async () => licenseManager.deactivate());
        registerTrustedIpcHandler('license:get-token', async () => licenseManager.getToken());
        registerTrustedIpcHandler('license:verify', async () => licenseManager.verifyOnline());
      } else {
        // Dev mode: expose permissive stubs so features are unlocked during development
        registerTrustedIpcHandler('license:get-status', async () => ({ active: true, plan: 'dev', exp: null }));
        registerTrustedIpcHandler('license:activate', async () => ({ ok: true, status: { active: true, plan: 'dev' } }));
        registerTrustedIpcHandler('license:activate-paypal-subscription', async () => ({ ok: true, status: { active: true, plan: 'dev' } }));
        registerTrustedIpcHandler('license:activate-paypal-purchase', async () => ({ ok: true, status: { active: true, plan: 'dev' } }));
        registerTrustedIpcHandler('license:deactivate', async () => ({ ok: true }));
        registerTrustedIpcHandler('license:get-token', async () => 'dev-token');
        registerTrustedIpcHandler('license:verify', async () => ({ ok: true }));
      }
    }
  } catch (e) {
    console.warn('License manager init failed:', e);
  }

  registerTrustedIpcHandler('license:open-paypal-checkout', async () => {
    const configuredServerUrl = app.isPackaged
      ? licenseManager?.serverUrl
      : (licenseManager?.serverUrl || RUNTIME_LICENSE_CONFIG.serverUrl || 'https://license.voxstella.app');
    const checkoutUrl = buildPayPalCheckoutUrl(configuredServerUrl);
    if (!checkoutUrl) {
      return { ok: false, error: 'checkout_url_unavailable' };
    }
    try {
      await shell.openExternal(checkoutUrl);
      return { ok: true };
    } catch (error) {
      return { ok: false, error: String(error?.message || error) };
    }
  });

  registerTrustedIpcHandler('shell:open-external', async (_event, rawUrl) => {
    if (typeof rawUrl !== 'string' || !rawUrl.trim()) return { ok: false, error: 'invalid_url' };
    if (!isAllowedExternalUrl(rawUrl)) return { ok: false, error: 'url_not_allowed' };
    try {
      await shell.openExternal(rawUrl);
      return { ok: true };
    } catch (error) {
      return { ok: false, error: String(error?.message || error) };
    }
  });

  registerTrustedIpcHandler('backend:get-status', async () => ({ status: backendStatus }));
  registerTrustedIpcHandler('backend:refresh-status', async () => {
    const status = await refreshBackendStatus({ timeoutMs: BACKEND_STATUS_PING_TIMEOUT_MS, forceBroadcast: true });
    return { status };
  });

  registerTrustedIpcHandler('diagnostics:get-log-paths', async () => ({ ok: true, ...getDiagnosticsLogPaths() }));
  registerTrustedIpcHandler('diagnostics:open-log-folder', async () => {
    const paths = getDiagnosticsLogPaths();
    if (!paths.logDir) return { ok: false, error: 'log_dir_unavailable' };
    ensureLogDir(paths.logDir);
    try {
      const error = await shell.openPath(paths.logDir);
      if (error) return { ok: false, error, path: paths.logDir };
      return { ok: true, path: paths.logDir, ...paths };
    } catch (err) {
      return { ok: false, error: String(err?.message || err), path: paths.logDir };
    }
  });
  registerTrustedIpcHandler('mcp:get-setup', async () => getMcpSetupStatus());
  registerTrustedIpcHandler('mcp:copy-config', async (_event, format) => {
    if (format !== 'json' && format !== 'codex') {
      return { ok: false, error: 'invalid_format' };
    }
    const setup = await getMcpSetupStatus();
    if (!setup.supported || !setup.launcherExists) {
      return { ok: false, error: setup.state };
    }
    clipboard.writeText(setup.configurations[format]);
    return { ok: true, format };
  });
  registerTrustedIpcHandler('mcp:open-launcher-folder', async () => {
    const setup = await getMcpSetupStatus();
    if (!setup.supported || !setup.launcherExists) {
      return { ok: false, error: setup.state };
    }
    shell.showItemInFolder(setup.launcherPath);
    return { ok: true, path: setup.launcherPath };
  });
  registerTrustedIpcHandler('report:export', handleReportExport);
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 880,
    minWidth: 720,
    minHeight: 600,
    backgroundColor: '#0b1020',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      navigateOnDragDrop: false,
    },
    show: false,
  });
  mainWindow = window;
  denySessionPermissions(window.webContents.session, { allowTrustedClipboardWrite: true });

  let windowShown = false;
  const showMainWindow = () => {
    if (windowShown || window.isDestroyed()) return;
    windowShown = true;
    window.show();
  };
  window.once('ready-to-show', showMainWindow);
  window.webContents.once('did-finish-load', () => setTimeout(showMainWindow, 250));
  const showFallbackTimer = setTimeout(showMainWindow, 5000);
  if (typeof showFallbackTimer.unref === 'function') {
    showFallbackTimer.unref();
  }

  window.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedExternalUrl(url)) {
      shell.openExternal(url).catch(() => {});
    }
    return { action: 'deny' };
  });
  const guardNavigation = (event, url) => {
    if (isAllowedAppNavigation(url)) return;
    event.preventDefault();
    if (isAllowedExternalUrl(url)) {
      shell.openExternal(url).catch(() => {});
    }
  };
  window.webContents.on('will-navigate', guardNavigation);
  window.webContents.on('will-redirect', guardNavigation);
  window.webContents.on('will-attach-webview', (event) => event.preventDefault());

  // Inject API base early via preload (window.API_BASE_URL)
  process.env.API_BASE_URL = API_BASE_URL;

  if (!app.isPackaged) {
    // Dev: load Vite dev server or local file
    await window.loadURL('http://localhost:5173/index.html');
  } else {
    // Prod: load built files
    await window.loadFile(PACKAGED_RENDERER_ENTRY);
  }

  broadcastBackendStatus();
  if (secondInstanceFocusPending) {
    secondInstanceFocusPending = false;
    focusWindow(window);
  }
  window.on('closed', () => {
    clearTimeout(showFallbackTimer);
    if (mainWindow === window) mainWindow = null;
  });
  return window;
}

async function waitForSmokeReadiness(timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastVersionResponse = null;
  let lastHealthResponse = null;
  while (Date.now() < deadline) {
    lastVersionResponse = await requestBackendJson('/api/version', 3000);
    if (lastVersionResponse.ok && isReachableVersionPayload(lastVersionResponse.payload)) {
      lastHealthResponse = await requestBackendJson('/api/health?skip_network=true', 10000);
      if (lastHealthResponse.ok && lastHealthResponse.payload?.ready === true) {
        return {
          versionPayload: lastVersionResponse.payload,
          healthPayload: lastHealthResponse.payload,
        };
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  const versionError = lastVersionResponse?.error || `http_${lastVersionResponse?.statusCode || 'unavailable'}`;
  const healthError = lastHealthResponse?.error || `http_${lastHealthResponse?.statusCode || 'unavailable'}`;
  throw new Error(`backend readiness timed out (version=${versionError}, health=${healthError})`);
}

async function runSmokeTest() {
  if (!app.isPackaged) {
    throw new Error('packaged smoke test must run from a packaged Electron application');
  }
  if (!backendProc) {
    throw new Error('packaged backend process did not start');
  }
  const configuredTimeout = Number(process.env.VOX_STELLA_SMOKE_TIMEOUT_MS || 60000);
  const timeoutMs = Number.isFinite(configuredTimeout)
    ? Math.min(Math.max(Math.floor(configuredTimeout), 5000), 180000)
    : 60000;
  const { versionPayload, healthPayload } = await waitForSmokeReadiness(timeoutMs);
  const result = validatePackagedBackendSmoke(versionPayload, healthPayload, {
    expectedVersion: app.getVersion(),
    expectedCommit: process.env.VOX_STELLA_EXPECTED_COMMIT,
    requireCleanBuild: process.env.VOX_STELLA_SMOKE_REQUIRE_CLEAN_BUILD === '1',
  });
  if (!result.ok) {
    throw new Error(result.errors.join('; '));
  }
  if (!/^[0-9a-f]{64}$/.test(packagedLicensePublicKeySha256 || '')) {
    throw new Error('packaged licensing trust-root fingerprint is unavailable');
  }
  result.licensePublicKeySha256 = packagedLicensePublicKeySha256;
  console.log(`[smoke] PASS ${JSON.stringify(result)}`);
  return result;
}

async function startInitialBackend(logDir) {
  if (!app.isPackaged) {
    return startBackend(logDir);
  }
  const maxAttempts = CONFIGURED_BACKEND_PORT ? 1 : 3;
  initialBackendReadinessPending = true;
  try {
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      if (attempt > 1) {
        const retryPort = await resolveBackendPort({
          appIsPackaged: true,
          configuredPort: CONFIGURED_BACKEND_PORT,
        });
        applyBackendPort(retryPort);
        configureRuntimeEnv({ appIsPackaged: true, apiBaseUrl: API_BASE_URL, env: process.env });
        console.warn(`[backend] retrying initial authenticated startup on port ${PORT}`);
      }
      backendProc = await startBackend(logDir);
      if (backendProc && await waitForBackendReachability(BACKEND_STATUS_BOOT_GRACE_MS)) {
        backendRestartAttempts = 0;
        setBackendStatus('connected', { force: true });
        return backendProc;
      }
      const failedChild = backendProc;
      backendProc = null;
      await terminateBackendChild(failedChild);
    }
  } finally {
    initialBackendReadinessPending = false;
  }
  throw new Error('Packaged backend failed authenticated readiness checks');
}

async function startApplication() {
  let logDir = null;
  try {
    logDir = path.join(app.getPath('userData'), 'logs');
  } catch (_) {}
  backendLogDir = logDir;
  configureMainFileLogging(logDir);
  const selectedPort = await resolveBackendPort({
    appIsPackaged: app.isPackaged,
    configuredPort: CONFIGURED_BACKEND_PORT,
  });
  applyBackendPort(selectedPort);
  console.log(`[backend] selected port ${PORT} (${app.isPackaged ? 'packaged' : 'development'} runtime)`);
  configureMapTileRequestHeaders();
  configureRendererSessionSecurity();
  configureRuntimeEnv({ appIsPackaged: app.isPackaged, apiBaseUrl: API_BASE_URL, env: process.env });
  backendProc = await startInitialBackend(logDir);
  if (SMOKE_TEST_MODE) {
    let exitCode = 0;
    try {
      const result = await runSmokeTest();
      const resultPath = writeSmokeResultFile(
        process.env.VOX_STELLA_SMOKE_RESULT_PATH,
        { ok: true, result },
      );
      if (resultPath) console.log(`[smoke] result file: ${resultPath}`);
    } catch (error) {
      exitCode = 1;
      const errorMessage = String(error?.message || error);
      console.error(`[smoke] FAIL ${errorMessage}`);
      try {
        writeSmokeResultFile(
          process.env.VOX_STELLA_SMOKE_RESULT_PATH,
          { ok: false, error: errorMessage },
        );
      } catch (resultError) {
        console.error(`[smoke] result file failed: ${String(resultError?.message || resultError)}`);
      }
    } finally {
      shutdownBackend();
      process.exitCode = exitCode;
      app.exit(exitCode);
    }
    return;
  }
  registerCoreIpcHandlers();
  await createWindow();
  startBackendStatusMonitor();
  void refreshBackendStatus({ timeoutMs: BACKEND_STATUS_PING_TIMEOUT_MS, forceBroadcast: true }).then((status) => {
    console.log(`Backend health: ${status}`);
  });

  // Initialize auto-updater IPC (no-op if module not installed)
  try {
    if (initAutoUpdater) {
      initAutoUpdater(ipcMain, () => mainWindow, { authorizeIpc: isTrustedIpcEvent });
    }
  } catch (e) {
    console.warn('Updater init failed:', e);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) void createWindow();
  });
}

async function startMcpApplication() {
  let logDir = null;
  try {
    logDir = path.join(app.getPath('userData'), 'logs');
  } catch (_) {}
  backendLogDir = logDir;
  configureMainFileLogging(logDir);
  const encodedMcpBrokerPipe = MCP_BROKER_MODE
    ? String(process.env.VOX_STELLA_MCP_PIPE_B64 || '')
    : '';
  const mcpBrokerSecret = MCP_BROKER_MODE
    ? String(process.env.VOX_STELLA_MCP_BRIDGE_SECRET || '')
    : '';
  let mcpBrokerPipeName = '';
  if (MCP_BROKER_MODE) {
    // Do not propagate the one-time bridge capability into the backend child.
    delete process.env.VOX_STELLA_MCP_PIPE_B64;
    delete process.env.VOX_STELLA_MCP_BRIDGE_SECRET;
    try {
      mcpBrokerPipeName = Buffer.from(encodedMcpBrokerPipe, 'base64').toString('utf8');
    } catch (_) {}
    if (!/^\\\\\.\\pipe\\vox-stella-mcp-[A-Za-z0-9-]+$/.test(mcpBrokerPipeName)) {
      throw new Error('Invalid MCP broker pipe');
    }
    if (!/^[0-9a-f]{64}$/.test(mcpBrokerSecret)) {
      throw new Error('Invalid MCP broker authentication');
    }
  }

  const {
    assertLicensedMcpAccess,
    createLicensedBackendClient,
  } = require('./main/mcp/licensed-backend-client');
  const { createVoxStellaMcpServer } = require('./main/mcp/server');
  const { serveStdio, StdioServerTransport } = require('@modelcontextprotocol/server/stdio');

  await ensureMcpLicenseSecurityContext();
  // Check before starting the calculation process and before advertising any
  // MCP capability. A copied config is useless on an unlicensed device.
  await assertLicensedMcpAccess(licenseManager);

  const selectedPort = await resolveBackendPort({
    appIsPackaged: app.isPackaged,
    configuredPort: CONFIGURED_BACKEND_PORT,
  });
  applyBackendPort(selectedPort);
  configureRuntimeEnv({ appIsPackaged: app.isPackaged, apiBaseUrl: API_BASE_URL, env: process.env });
  backendProc = await startInitialBackend(logDir);
  if (!app.isPackaged && !(await waitForBackendReachability(BACKEND_STATUS_BOOT_GRACE_MS))) {
    throw new Error('Vox Stella calculation backend did not become ready');
  }

  const licensedBackendCall = createLicensedBackendClient({
    apiBaseUrl: API_BASE_URL,
    licenseManager,
  });
  let brokerSocket = null;
  let mcpTransport = null;
  if (MCP_BROKER_MODE) {
    brokerSocket = await new Promise((resolve, reject) => {
      const socket = net.createConnection(mcpBrokerPipeName);
      const timer = setTimeout(() => {
        socket.destroy();
        reject(new Error('Timed out connecting to the MCP console bridge'));
      }, 15000);
      socket.once('connect', () => {
        clearTimeout(timer);
        resolve(socket);
      });
      socket.once('error', (error) => {
        clearTimeout(timer);
        reject(error);
      });
    });
    brokerSocket.write(`${JSON.stringify({
      protocol: 'vox-stella-mcp-bridge-v1',
      secret: mcpBrokerSecret,
    })}\n`);
    mcpTransport = new StdioServerTransport(brokerSocket, brokerSocket);
  }

  const mcpHandle = serveStdio(
    () => createVoxStellaMcpServer({
      appVersion: app.getVersion(),
      licensedBackendCall,
    }),
    {
      legacy: 'serve',
      ...(mcpTransport ? { transport: mcpTransport } : {}),
      onerror: (error) => console.error(`[mcp] ${String(error?.message || error)}`),
    },
  );
  console.error(`[mcp] Vox Stella ${app.getVersion()} licensed stdio server ready`);

  const shutdownMcp = () => {
    void mcpHandle.close().catch(() => null).finally(() => {
      shutdownBackend();
      app.quit();
    });
  };
  if (brokerSocket) {
    brokerSocket.once('close', shutdownMcp);
    brokerSocket.once('error', (error) => {
      console.error(`[mcp] bridge disconnected: ${String(error?.message || error)}`);
    });
  } else {
    process.stdin.once('end', shutdownMcp);
  }
}

function withTimeout(promise, timeoutMs, label) {
  let timer = null;
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${label} timed out`)), timeoutMs);
    }),
  ]).finally(() => {
    if (timer) clearTimeout(timer);
  });
}

function configureReportWindowSecurity(win, expectedUrl) {
  denySessionPermissions(win.webContents.session);
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-attach-webview', (event) => event.preventDefault());
  win.webContents.on('will-navigate', (event, url) => {
    if (url === expectedUrl) return;
    event.preventDefault();
  });
  win.webContents.on('will-redirect', (event) => event.preventDefault());
  try {
    win.webContents.session.webRequest.onBeforeRequest(
      { urls: ['<all_urls>'] },
      (_details, callback) => callback({ cancel: true }),
    );
  } catch (_) {}
}

async function handleReportExport(_event, payload) {
  let win = null;
  try {
    const {
      html,
      pageSize,
      title,
      defaultPath,
    } = validateReportPayload(payload);
    const saveDialogOptions = {
      title,
      defaultPath,
      filters: [{ name: 'PDF', extensions: ['pdf'] }],
      properties: ['showOverwriteConfirmation', 'createDirectory'],
    };
    const saveResult = mainWindow && !mainWindow.isDestroyed()
      ? await dialog.showSaveDialog(mainWindow, saveDialogOptions)
      : await dialog.showSaveDialog(saveDialogOptions);
    if (saveResult.canceled || !saveResult.filePath) {
      return { ok: false, error: 'Save canceled' };
    }
    const filePath = /\.pdf$/i.test(saveResult.filePath)
      ? saveResult.filePath
      : `${saveResult.filePath}.pdf`;
    const reportUrl = `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
    win = new BrowserWindow({
      show: false,
      webPreferences: {
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
        javascript: false,
        webSecurity: true,
        allowRunningInsecureContent: false,
        navigateOnDragDrop: false,
        partition: 'report-export',
      },
    });
    configureReportWindowSecurity(win, reportUrl);
    await withTimeout(win.loadURL(reportUrl), 15000, 'Report rendering');
    const pdf = await withTimeout(win.webContents.printToPDF({
      marginsType: 1,
      printBackground: true,
      pageSize,
      landscape: false,
    }), 30000, 'PDF generation');
    await fs.promises.writeFile(filePath, pdf, { flag: 'w' });
    return { ok: true, path: filePath };
  } catch (e) {
    console.error('report:export failed:', e);
    return { ok: false, error: String(e?.message || e) };
  } finally {
    try {
      if (win && !win.isDestroyed()) win.destroy();
    } catch (_) {}
  }
}

function shutdownBackend() {
  if (backendKillStarted) return;
  backendKillStarted = true;
  closed = true;
  clearBackendRestartTimer();
  backendRestartAttempts = 0;
  stopBackendStatusMonitor();
  stopBackendHeartbeat();
  if (backendProc && backendProc.exitCode == null && backendProc.signalCode == null) {
    try {
      if (process.platform === 'win32') {
        // Graceful first
        try { backendProc.kill('SIGTERM'); } catch (_) {}
        // Synchronous tree kill to avoid timers being skipped on app quit
        try {
          spawnSync('taskkill', ['/PID', String(backendProc.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
        } catch (_) {}
      } else {
        try { backendProc.kill('SIGTERM'); } catch (_) {}
        try {
          const t = setTimeout(() => { try { backendProc.kill('SIGKILL'); } catch (_) {} }, 800);
          // Give a moment for SIGTERM
          setTimeout(() => clearTimeout(t), 900);
        } catch (_) {}
      }
    } catch (_) { /* ignore */ }
  }
}

function terminateApplication(reason, error, exitCode) {
  if (fatalExitStarted) return;
  fatalExitStarted = true;
  const detail = error instanceof Error
    ? (error.stack || error.message)
    : String(error || reason);
  console.error(`[fatal] ${reason}: ${detail}`);
  shutdownBackend();
  process.exitCode = exitCode;
  try {
    app.exit(exitCode);
  } catch (_) {}
}

if (hasSingleInstanceLock) {
  app.on('before-quit', shutdownBackend);
  app.on('will-quit', shutdownBackend);
  app.on('window-all-closed', () => {
    if (MCP_MODE) return;
    if (process.platform !== 'darwin') {
      shutdownBackend();
      app.quit();
    }
  });

  // Extra safety: kill backend on process exit or signals
  process.once('exit', shutdownBackend);
  process.once('SIGINT', () => terminateApplication('SIGINT', 'interrupt signal', 130));
  process.once('SIGTERM', () => terminateApplication('SIGTERM', 'termination signal', 143));
  process.once('uncaughtException', (error) => terminateApplication('uncaughtException', error, 1));
  process.once('unhandledRejection', (reason) => terminateApplication('unhandledRejection', reason, 1));

  app.whenReady()
    .then(MCP_MODE ? startMcpApplication : startApplication)
    .catch((error) => {
      if (SMOKE_TEST_MODE) {
        try {
          writeSmokeResultFile(
            process.env.VOX_STELLA_SMOKE_RESULT_PATH,
            { ok: false, error: String(error?.message || error) },
          );
        } catch (resultError) {
          console.error(`[smoke] result file failed: ${String(resultError?.message || resultError)}`);
        }
      }
      terminateApplication('startup', error, 1);
    });
}
