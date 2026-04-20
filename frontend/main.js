// Electron main process: creates window, starts backend, injects API base, and cleans up.
const { app, BrowserWindow, ipcMain, dialog, shell, session } = require('electron');
const path = require('path');
const crypto = require('crypto');
const { spawn, spawnSync } = require('child_process');
const http = require('http');
const fs = require('fs');
const {
  DEFAULT_BACKEND_PORT,
  buildAppOrigins,
  buildBackendLocalOrigins,
  createApiBaseUrl,
  normalizePort,
  resolveBackendPort,
} = require('./main/backend-port');
const { configureRuntimeEnv } = require('./main/runtime-env');
// Optional modules (exist if installed)
let initAutoUpdater; try { ({ initAutoUpdater } = require('./main/updater')); } catch (_) {}
let LicenseManager; try { ({ LicenseManager } = require('./main/license')); } catch (_) {}

const CONFIGURED_BACKEND_PORT = process.env.HORARY_PORT;
let PORT = normalizePort(CONFIGURED_BACKEND_PORT, DEFAULT_BACKEND_PORT);
let API_BASE_URL = createApiBaseUrl(PORT);
let BACKEND_LOCAL_ORIGINS = buildBackendLocalOrigins(PORT);
let APP_ORIGINS = buildAppOrigins(PORT);
const EXTERNAL_HOST_ALLOWLIST = new Set([
  'voxstella.app',
  'www.voxstella.app',
]);
const OSM_TILE_HOST_SUFFIX = '.tile.openstreetmap.org';
const OSM_TILE_REFERER = 'https://voxstella.app/';

function applyBackendPort(nextPort) {
  PORT = normalizePort(nextPort, DEFAULT_BACKEND_PORT);
  API_BASE_URL = createApiBaseUrl(PORT);
  BACKEND_LOCAL_ORIGINS = buildBackendLocalOrigins(PORT);
  APP_ORIGINS = buildAppOrigins(PORT);
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

let mainWindow = null;
let backendProc = null;
let closed = false;
let backendKillStarted = false;
let licenseManager = null;
let backendLogDir = null;
let backendRestartAttempts = 0;
let backendRestartTimer = null;
let backendParentStateFile = null;
let backendHeartbeatTimer = null;
let ipcHandlersRegistered = false;
let backendLicenseSessionSecretB64 = null;
let backendStatus = 'checking';
let backendStartupDeadlineMs = 0;
let backendStatusPollTimer = null;
let backendStatusProbePromise = null;
let backendConsecutiveProbeFailures = 0;
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

function probeBackendReachabilityOnce(timeoutMs = BACKEND_STATUS_PING_TIMEOUT_MS) {
  return new Promise((resolve) => {
    const req = http.get(`${API_BASE_URL}/api/version`, { timeout: timeoutMs }, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        if (body.length < 32768) body += chunk;
      });
      res.on('end', () => {
        if (res.statusCode !== 200) {
          resolve(false);
          return;
        }
        try {
          const parsed = JSON.parse(body || '{}');
          resolve(isReachableVersionPayload(parsed));
        } catch (_) {
          resolve(false);
        }
      });
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
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
  if (backendParentStateFile) return backendParentStateFile;
  const baseDir = logDir || app.getPath('userData');
  try {
    if (!fs.existsSync(baseDir)) fs.mkdirSync(baseDir, { recursive: true });
  } catch (_) {}
  backendParentStateFile = path.join(baseDir, 'backend-parent-state.json');
  return backendParentStateFile;
}

function writeBackendParentState() {
  const stateFile = backendParentStateFile;
  if (!stateFile) return;
  try {
    fs.writeFileSync(stateFile, JSON.stringify({
      pid: process.pid,
      updated_at_ms: Date.now(),
    }), 'utf8');
  } catch (_) {}
}

function startBackendHeartbeat(logDir) {
  const stateFile = ensureBackendParentStateFile(logDir);
  if (!stateFile) return null;
  writeBackendParentState();
  if (backendHeartbeatTimer) clearInterval(backendHeartbeatTimer);
  backendHeartbeatTimer = setInterval(writeBackendParentState, 1000);
  if (typeof backendHeartbeatTimer.unref === 'function') {
    backendHeartbeatTimer.unref();
  }
  return stateFile;
}

function stopBackendHeartbeat() {
  if (backendHeartbeatTimer) {
    clearInterval(backendHeartbeatTimer);
    backendHeartbeatTimer = null;
  }
  if (backendParentStateFile) {
    try { fs.unlinkSync(backendParentStateFile); } catch (_) {}
    backendParentStateFile = null;
  }
}

function isAllowedExternalUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    const host = (parsed.hostname || '').toLowerCase();
    const origin = parsed.origin;
    if (BACKEND_LOCAL_ORIGINS.has(origin)) return true;
    if (parsed.protocol !== 'https:') return false;
    if (EXTERNAL_HOST_ALLOWLIST.has(host)) return true;
    return false;
  } catch (_) {
    return false;
  }
}

function isAllowedAppNavigation(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    if (parsed.protocol === 'file:') return true;
    return APP_ORIGINS.has(parsed.origin);
  } catch (_) {
    return false;
  }
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
  if (!app.isPackaged || !LicenseManager) return;
  if (!licenseManager) {
    licenseManager = new LicenseManager(app);
  }
  const deviceId = await licenseManager.getDeviceId().catch(() => null);
  if (deviceId) {
    process.env.VOX_STELLA_DEVICE_ID = deviceId;
  }
  if (!backendLicenseSessionSecretB64) {
    backendLicenseSessionSecretB64 = crypto.randomBytes(32).toString('base64');
  }
  process.env.VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64 = backendLicenseSessionSecretB64;
}

async function startBackend(logDir) {
  console.log('=== Starting Backend ===');
  markBackendStarting();
  const resolved = resolveBackendCommand();
  if (!resolved) {
    console.warn('Backend executable not found. Assuming an external backend is running.');
    return null;
  }
  await ensurePackagedLicenseSecurityContext();
  const parentStateFile = startBackendHeartbeat(logDir);
  const env = { ...process.env, HORARY_PORT: String(PORT) };
  const captureBackendToFile = !app.isPackaged || process.env.VOX_STELLA_CAPTURE_BACKEND_STDIO === '1';
  env.VOX_STELLA_PARENT_PID = String(process.pid);
  env.VOX_STELLA_APP_VERSION = app.getVersion();
  if (parentStateFile) env.VOX_STELLA_PARENT_STATE_FILE = parentStateFile;
  // Never inherit license bypass flags unless explicitly enabled in dev.
  delete env.LICENSE_BYPASS;
  delete env.ALLOW_DEV_LICENSE_BYPASS;
  env.APP_IS_PACKAGED = app.isPackaged ? '1' : '0';
  if (!app.isPackaged && process.env.ALLOW_DEV_LICENSE_BYPASS === '1') {
    env.ALLOW_DEV_LICENSE_BYPASS = '1';
  }
  if (!env.LICENSE_PUBLIC_KEY_B64 && RUNTIME_LICENSE_CONFIG.publicKeyB64) {
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
    // Keep stdout/stderr drained, but avoid persisting chart payloads in packaged builds
    // unless log capture is explicitly enabled for diagnostics.
    try {
      let logStream = null;
      let logPath = null;
      if (captureBackendToFile) {
        if (logDir && !fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
        logPath = logDir ? path.join(logDir, 'backend.log') : path.join(resolved.cwd, 'backend.log');
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
          scheduleBackendRestart(`exit:${code ?? 'unknown'}`);
        }
      }
    });
    
    child.on('error', (error) => {
      console.error('Backend process error:', error);
      if (!closed && !backendKillStarted) {
        if (backendProc && backendProc.pid === child.pid) {
          markBackendStarting();
          scheduleBackendRestart('spawn-error');
        }
      }
    });
    
    return child;
  } catch (error) {
    console.error('Failed to spawn backend process:', error);
    return null;
  }
}

function scheduleBackendRestart(reason = 'unknown') {
  if (!app.isPackaged || closed || backendKillStarted) return;
  markBackendStarting();
  if (backendRestartTimer) return;
  if (backendRestartAttempts >= MAX_BACKEND_RESTARTS) {
    console.error(`[backend] restart limit reached (${MAX_BACKEND_RESTARTS}). Last reason: ${reason}`);
    return;
  }
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
    try {
      if (backendProc && !backendProc.killed) {
        backendProc.kill('SIGTERM');
      }
    } catch (_) {}
    scheduleBackendRestart('restart-timeout');
  }, delayMs);
}

function waitForBackendReachability(timeoutMs = 12000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve) => {
    const attempt = () => {
      if (Date.now() > deadline) return resolve(false);
      const req = http.get(`${API_BASE_URL}/api/version`, { timeout: 1500 }, (res) => {
        let body = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => {
          if (body.length < 32768) body += chunk;
        });
        res.on('end', () => {
          if (res.statusCode !== 200) {
            setTimeout(attempt, 400);
            return;
          }
          try {
            const parsed = JSON.parse(body || '{}');
            if (isReachableVersionPayload(parsed)) {
              resolve(true);
              return;
            }
          } catch (_) {}
          setTimeout(attempt, 400);
        });
      });
      req.on('error', () => setTimeout(attempt, 400));
      req.on('timeout', () => { req.destroy(); setTimeout(attempt, 300); });
    };
    attempt();
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
        ipcMain.handle('license:get-status', async () => licenseManager.getStatus());
        ipcMain.handle('license:activate', async (_e, payload) => {
          const result = await licenseManager.activate(payload || {});
          return result;
        });
        ipcMain.handle('license:deactivate', async () => licenseManager.deactivate());
        ipcMain.handle('license:get-token', async () => licenseManager.getToken());
        ipcMain.handle('license:verify', async () => licenseManager.verifyOnline());
      } else {
        // Dev mode: expose permissive stubs so features are unlocked during development
        ipcMain.handle('license:get-status', async () => ({ active: true, plan: 'dev', exp: null }));
        ipcMain.handle('license:activate', async () => ({ ok: true, status: { active: true, plan: 'dev' } }));
        ipcMain.handle('license:deactivate', async () => ({ ok: true }));
        ipcMain.handle('license:get-token', async () => 'dev-token');
        ipcMain.handle('license:verify', async () => ({ ok: true }));
      }
    }
  } catch (e) {
    console.warn('License manager init failed:', e);
  }

  ipcMain.handle('shell:open-external', async (_event, rawUrl) => {
    if (typeof rawUrl !== 'string' || !rawUrl.trim()) return { ok: false, error: 'invalid_url' };
    if (!isAllowedExternalUrl(rawUrl)) return { ok: false, error: 'url_not_allowed' };
    try {
      await shell.openExternal(rawUrl);
      return { ok: true };
    } catch (error) {
      return { ok: false, error: String(error?.message || error) };
    }
  });

  ipcMain.handle('backend:get-status', async () => ({ status: backendStatus }));
  ipcMain.handle('backend:refresh-status', async () => {
    const status = await refreshBackendStatus({ timeoutMs: BACKEND_STATUS_PING_TIMEOUT_MS, forceBroadcast: true });
    return { status };
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 880,
    backgroundColor: '#0b1020',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    show: false,
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedExternalUrl(url)) {
      shell.openExternal(url).catch(() => {});
    }
    return { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (isAllowedAppNavigation(url)) return;
    event.preventDefault();
    if (isAllowedExternalUrl(url)) {
      shell.openExternal(url).catch(() => {});
    }
  });

  // Inject API base early via preload (window.API_BASE_URL)
  process.env.API_BASE_URL = API_BASE_URL;

  if (!app.isPackaged) {
    // Dev: load Vite dev server or local file
    await mainWindow.loadURL('http://localhost:5173/index.html');
  } else {
    // Prod: load built files
    await mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => mainWindow.show());
  broadcastBackendStatus();
  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(async () => {
  let logDir = null;
  try {
    logDir = path.join(app.getPath('userData'), 'logs');
  } catch (_) {}
  backendLogDir = logDir;
  const selectedPort = await resolveBackendPort({
    appIsPackaged: app.isPackaged,
    configuredPort: CONFIGURED_BACKEND_PORT,
  });
  applyBackendPort(selectedPort);
  console.log(`[backend] selected port ${PORT} (${app.isPackaged ? 'packaged' : 'development'} runtime)`);
  configureMapTileRequestHeaders();
  configureRuntimeEnv({ appIsPackaged: app.isPackaged, apiBaseUrl: API_BASE_URL, env: process.env });
  backendProc = await startBackend(logDir);
  registerCoreIpcHandlers();
  await createWindow();
  startBackendStatusMonitor();
  void refreshBackendStatus({ timeoutMs: BACKEND_STATUS_PING_TIMEOUT_MS, forceBroadcast: true }).then((status) => {
    console.log(`Backend health: ${status}`);
  });

  // Initialize auto-updater IPC (no-op if module not installed)
  try { if (initAutoUpdater) initAutoUpdater(ipcMain, mainWindow); } catch (e) { console.warn('Updater init failed:', e); }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Report export: render provided HTML in an offscreen window and save as PDF
function sanitizeReportHtml(input) {
  let html = String(input || '');
  // Strip scripts and inline handlers from renderer-provided markup.
  html = html.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '');
  html = html.replace(/\son\w+=(\"[^\"]*\"|'[^']*'|[^\s>]+)/gi, '');
  html = html.replace(/javascript:/gi, '');
  return html;
}

ipcMain.handle('report:export', async (_e, payload) => {
  try {
    const html = String(payload?.html || '');
    const pageSize = payload?.pageSize || 'A4';
    if (!html) throw new Error('Empty report HTML');
    const safeHtml = sanitizeReportHtml(html);

    const win = new BrowserWindow({
      show: false,
      webPreferences: {
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
        javascript: false,
      },
    });
    await win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(safeHtml));
    // Wait a short moment for fonts/images
    await new Promise(r => setTimeout(r, 200));
    const pdf = await win.webContents.printToPDF({
      marginsType: 1,
      printBackground: true,
      pageSize,
      landscape: false,
    });
    win.destroy();

    const { filePath, canceled } = await dialog.showSaveDialog({
      title: 'Save Forensic Report',
      defaultPath: 'ForensicReport.pdf',
      filters: [{ name: 'PDF', extensions: ['pdf'] }],
    });
    if (canceled || !filePath) return { ok: false, error: 'Save canceled' };
    fs.writeFileSync(filePath, pdf);
    return { ok: true, path: filePath };
  } catch (e) {
    console.error('report:export failed:', e);
    return { ok: false, error: String(e?.message || e) };
  }
});

function shutdownBackend() {
  if (backendKillStarted) return;
  backendKillStarted = true;
  closed = true;
  clearBackendRestartTimer();
  backendRestartAttempts = 0;
  stopBackendStatusMonitor();
  stopBackendHeartbeat();
  if (backendProc && !backendProc.killed) {
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

app.on('before-quit', shutdownBackend);
app.on('will-quit', shutdownBackend);
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    shutdownBackend();
    app.quit();
  }
});

// Extra safety: kill backend on process exit or signals
process.on('exit', shutdownBackend);
process.on('SIGINT', shutdownBackend);
process.on('SIGTERM', shutdownBackend);
process.on('uncaughtException', shutdownBackend);
process.on('unhandledRejection', shutdownBackend);
