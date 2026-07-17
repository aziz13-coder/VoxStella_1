const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const http = require('node:http');
const { EventEmitter } = require('node:events');
const { pathToFileURL } = require('node:url');

const {
  MAX_REPORT_HTML_BYTES,
  PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
  PRODUCTION_LICENSE_SERVER_ORIGIN,
  buildPayPalCheckoutUrl,
  isAllowedExternalUrl,
  isAllowedRendererUrl,
  validatePackagedLicenseConfig,
  validateReportPayload,
} = require('../main/security-policy');
const {
  validatePackagedBackendSmoke,
  writeSmokeResultFile,
} = require('../main/smoke-contract');
const { initAutoUpdater } = require('../main/updater');
const {
  createBackendInstanceProof,
  verifyBackendInstanceProof,
} = require('../main/backend-instance-auth');
const { requestJsonWithDeadline } = require('../main/backend-http');

test('external URL policy allows browser-safe destinations and rejects dangerous schemes', () => {
  assert.equal(isAllowedExternalUrl('https://example.com/reference?q=1'), true);
  assert.equal(isAllowedExternalUrl('mailto:support@example.com?subject=Help'), true);
  assert.equal(isAllowedExternalUrl('http://example.com'), false);
  assert.equal(isAllowedExternalUrl('javascript:alert(1)'), false);
  assert.equal(isAllowedExternalUrl('https://user:secret@example.com/'), false);
  assert.equal(isAllowedExternalUrl('mailto:support@example.com?subject=x%0aBcc:y@example.com'), false);
  assert.equal(isAllowedExternalUrl('https://example.com/\nnext'), false);
});

test('PayPal checkout destination is fixed to the configured HTTPS licensing origin', () => {
  assert.equal(
    buildPayPalCheckoutUrl('https://licenses.example.test/api/'),
    'https://licenses.example.test/checkout/desktop-monthly',
  );
  assert.equal(buildPayPalCheckoutUrl('http://licenses.example.test'), null);
  assert.equal(buildPayPalCheckoutUrl('https://user:secret@licenses.example.test'), null);
  assert.equal(buildPayPalCheckoutUrl('javascript:alert(1)'), null);
});

test('packaged license configuration requires an HTTPS server and Ed25519 public key', () => {
  const publicKeyB64 = Buffer.alloc(32, 7).toString('base64');
  assert.deepEqual(
    validatePackagedLicenseConfig({
      serverUrl: 'https://license.example.test/',
      publicKeyB64,
    }),
    {
      serverUrl: 'https://license.example.test',
      publicKeyB64,
    },
  );
  assert.throws(
    () => validatePackagedLicenseConfig({ serverUrl: 'http://license.example.test', publicKeyB64 }),
    /HTTPS/,
  );
  assert.throws(
    () => validatePackagedLicenseConfig({ serverUrl: 'https://license.example.test', publicKeyB64: 'bad' }),
    /public key/,
  );
  assert.throws(
    () => validatePackagedLicenseConfig(null),
    /missing/,
  );
  assert.deepEqual(
    validatePackagedLicenseConfig(
      {
        serverUrl: PRODUCTION_LICENSE_SERVER_ORIGIN,
        publicKeyB64,
      },
      { expectedServerOrigin: PRODUCTION_LICENSE_SERVER_ORIGIN },
    ),
    {
      serverUrl: PRODUCTION_LICENSE_SERVER_ORIGIN,
      publicKeyB64,
    },
  );
  assert.throws(
    () => validatePackagedLicenseConfig(
      {
        serverUrl: 'https://attacker.example',
        publicKeyB64,
      },
      { expectedServerOrigin: PRODUCTION_LICENSE_SERVER_ORIGIN },
    ),
    /production trust root/,
  );
  const fakeKeyFingerprint = crypto.createHash('sha256')
    .update(Buffer.from(publicKeyB64, 'base64'))
    .digest('hex');
  assert.doesNotThrow(() => validatePackagedLicenseConfig(
    {
      serverUrl: PRODUCTION_LICENSE_SERVER_ORIGIN,
      publicKeyB64,
    },
    {
      expectedPublicKeySha256: fakeKeyFingerprint,
      expectedServerOrigin: PRODUCTION_LICENSE_SERVER_ORIGIN,
    },
  ));
  assert.throws(
    () => validatePackagedLicenseConfig(
      {
        serverUrl: PRODUCTION_LICENSE_SERVER_ORIGIN,
        publicKeyB64,
      },
      {
        expectedPublicKeySha256: PRODUCTION_LICENSE_PUBLIC_KEY_SHA256,
        expectedServerOrigin: PRODUCTION_LICENSE_SERVER_ORIGIN,
      },
    ),
    /public key does not match/,
  );
});

async function listenOnLoopback(server) {
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return `http://127.0.0.1:${server.address().port}`;
}

async function closeServer(server) {
  server.closeAllConnections?.();
  await new Promise((resolve) => server.close(resolve));
}

test('backend JSON requests enforce an absolute deadline and settle on partial responses', async () => {
  const successServer = http.createServer((_req, res) => {
    res.writeHead(200, {
      'content-type': 'application/json',
      'x-instance-proof': 'proof',
    });
    res.end('{"ready":true}');
  });
  const successOrigin = await listenOnLoopback(successServer);
  try {
    const result = await requestJsonWithDeadline(`${successOrigin}/api/health`, {
      timeoutMs: 500,
    });
    assert.equal(result.ok, true);
    assert.deepEqual(result.payload, { ready: true });
    assert.equal(result.headers['x-instance-proof'], 'proof');
  } finally {
    await closeServer(successServer);
  }

  const partialServer = http.createServer((_req, res) => {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.write('{"ready":');
    setImmediate(() => res.socket?.destroy());
  });
  const partialOrigin = await listenOnLoopback(partialServer);
  try {
    const result = await requestJsonWithDeadline(`${partialOrigin}/api/health`, {
      timeoutMs: 500,
    });
    assert.equal(result.ok, false);
    assert.match(result.error, /response_aborted|response_closed|socket hang up/);
  } finally {
    await closeServer(partialServer);
  }

  const trickleServer = http.createServer((_req, res) => {
    res.writeHead(200, { 'content-type': 'application/json' });
    const interval = setInterval(() => res.write(' '), 10);
    res.on('close', () => clearInterval(interval));
  });
  const trickleOrigin = await listenOnLoopback(trickleServer);
  try {
    const startedAt = Date.now();
    const result = await requestJsonWithDeadline(`${trickleOrigin}/api/health`, {
      timeoutMs: 80,
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, 'timeout');
    assert.ok(Date.now() - startedAt < 500, 'absolute deadline must bound slow trickle responses');
  } finally {
    await closeServer(trickleServer);
  }
});

test('backend instance proof binds a fresh challenge to the exact request pathname', () => {
  const secret = Buffer.alloc(32, 9).toString('base64');
  const challenge = Buffer.alloc(32, 4).toString('base64url');
  const proof = createBackendInstanceProof(secret, challenge, '/api/version');
  assert.match(proof, /^[0-9a-f]{64}$/);
  assert.equal(
    verifyBackendInstanceProof(secret, challenge, '/api/version', proof),
    true,
  );
  assert.equal(
    verifyBackendInstanceProof(secret, challenge, '/api/health', proof),
    false,
  );
  assert.equal(
    verifyBackendInstanceProof(secret, `${challenge.slice(0, -1)}x`, '/api/version', proof),
    false,
  );
});

test('renderer navigation policy accepts only the exact application document', () => {
  const entryPath = path.join(path.sep, 'opt', 'vox-stella', 'resources', 'app.asar', 'dist', 'index.html');
  const entryUrl = pathToFileURL(entryPath);
  entryUrl.search = '?source=test';
  entryUrl.hash = '#dashboard';

  assert.equal(isAllowedRendererUrl(entryUrl.href, {
    isPackaged: true,
    packagedEntryPath: entryPath,
  }), true);
  assert.equal(isAllowedRendererUrl(pathToFileURL(path.join(path.dirname(entryPath), 'other.html')).href, {
    isPackaged: true,
    packagedEntryPath: entryPath,
  }), false);
  assert.equal(isAllowedRendererUrl('file:///C:/Windows/System32/drivers/etc/hosts', {
    isPackaged: true,
    packagedEntryPath: entryPath,
  }), false);
  assert.equal(isAllowedRendererUrl('http://localhost:5173/index.html?dev=1', {
    isPackaged: false,
  }), true);
  assert.equal(isAllowedRendererUrl('http://localhost:5173/admin', {
    isPackaged: false,
  }), false);
  assert.equal(isAllowedRendererUrl('http://127.0.0.1:52525/api/version', {
    isPackaged: false,
  }), false);
});

test('report payload validation bounds input and removes active or remote content', () => {
  const validated = validateReportPayload({
    html: `<!doctype html><html><head>
      <meta http-equiv="Content-Security-Policy" content="default-src *">
      <meta http-equiv="refresh" content="0;url=https://attacker.example">
      <link rel="stylesheet" href="https://attacker.example/style.css">
      <style>@import "https://attacker.example/x.css"; .x{background:url(https://attacker.example/x)}</style>
      </head><body onload="steal()">
      <script>steal()</script><iframe src="https://attacker.example"></iframe>
      <img src="data:image/png;base64,AA==">
      </body></html>`,
    pageSize: 'Letter',
    title: ' Save\nReport ',
    defaultPath: '../unsafe:name',
  });

  assert.equal(validated.pageSize, 'Letter');
  assert.equal(validated.title, 'Save Report');
  assert.equal(validated.defaultPath, '.._unsafe_name.pdf');
  assert.match(validated.html, /Content-Security-Policy/);
  assert.match(validated.html, /script-src 'none'/);
  assert.doesNotMatch(validated.html, /<script/i);
  assert.doesNotMatch(validated.html, /\sonload=/i);
  assert.doesNotMatch(validated.html, /<iframe/i);
  assert.doesNotMatch(validated.html, /<link/i);
  assert.doesNotMatch(validated.html, /@import/i);
  assert.doesNotMatch(validated.html, /url\(https:/i);
  assert.match(validated.html, /data:image\/png/);

  assert.throws(
    () => validateReportPayload({ html: '<p>x</p>', pageSize: 'custom' }),
    /Unsupported report page size/,
  );
  assert.throws(
    () => validateReportPayload({ html: 'x'.repeat(MAX_REPORT_HTML_BYTES + 1) }),
    /exceeds/,
  );
});

test('packaged smoke contract requires ready, version-matched, commit-bearing metadata', () => {
  const commit = '0123456789abcdef0123456789abcdef01234567';
  const build = {
    metadata_source: 'file',
    runtime_kind: 'pyinstaller_bundle',
    git: {
      commit,
      tree: '89abcdef0123456789abcdef0123456789abcdef',
      dirty: false,
    },
  };
  const result = validatePackagedBackendSmoke(
    {
      app_version: '3.1.0',
      api_version: '2.0.0',
      backend_build: build,
    },
    {
      ready: true,
      status: 'healthy',
      version: '3.1.0',
      backend_build: build,
    },
    {
      expectedVersion: '3.1.0',
      expectedCommit: commit,
      requireCleanBuild: true,
    },
  );
  assert.equal(result.ok, true);
  assert.equal(result.commit, commit);

  const invalid = validatePackagedBackendSmoke(
    {
      app_version: '3.0.0',
      api_version: '2.0.0',
      backend_build: {
        metadata_source: 'runtime_probe',
        runtime_kind: 'source_runtime',
        git: { commit: 'short', dirty: true },
      },
    },
    {
      ready: false,
      status: 'unhealthy',
      version: '3.0.0',
      backend_build: { git: { commit: 'different' } },
    },
    {
      expectedVersion: '3.1.0',
      expectedCommit: commit,
      requireCleanBuild: true,
    },
  );
  assert.equal(invalid.ok, false);
  assert.match(invalid.errors.join('; '), /does not match|not ready|not clean|metadata source/i);
});

test('packaged smoke result file is written atomically for GUI-subsystem launches', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vox-stella-smoke-'));
  try {
    const resultPath = path.join(tempDir, 'result.json');
    assert.equal(
      writeSmokeResultFile(resultPath, { ok: true, result: { commit: 'abc' } }),
      resultPath,
    );
    assert.deepEqual(JSON.parse(fs.readFileSync(resultPath, 'utf8')), {
      schemaVersion: 1,
      ok: true,
      result: { commit: 'abc' },
    });
    assert.throws(
      () => writeSmokeResultFile('relative-result.json', { ok: true }),
      /must be absolute/,
    );
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});

function makeIpcMain() {
  const handlers = new Map();
  return {
    handlers,
    handle(channel, handler) {
      handlers.set(channel, handler);
    },
  };
}

function makeWindow() {
  const sent = [];
  return {
    sent,
    isDestroyed: () => false,
    webContents: {
      isDestroyed: () => false,
      send: (channel, payload) => sent.push({ channel, payload }),
    },
  };
}

test('updater reports terminal failures, validates IPC, and targets recreated windows', async () => {
  const ipcMain = makeIpcMain();
  const updater = new EventEmitter();
  updater.checkForUpdates = async () => {
    throw new Error('network unavailable');
  };
  updater.quitAndInstall = () => {};
  const firstWindow = makeWindow();
  const secondWindow = makeWindow();
  let currentWindow = firstWindow;

  initAutoUpdater(ipcMain, () => currentWindow, {
    autoUpdater: updater,
    authorizeIpc: (event) => event?.trusted === true,
  });

  const unauthorized = await ipcMain.handlers.get('update:check')({ trusted: false });
  assert.deepEqual(unauthorized, { ok: false, error: 'unauthorized_sender' });
  assert.equal(updater.autoDownload, true);

  const failed = await ipcMain.handlers.get('update:check')({ trusted: true });
  assert.deepEqual(failed, { ok: false, error: 'network unavailable' });
  assert.deepEqual(firstWindow.sent.at(-1), {
    channel: 'update:error',
    payload: 'network unavailable',
  });

  currentWindow = secondWindow;
  updater.emit('update-available', { version: '4.0.0' });
  assert.deepEqual(secondWindow.sent.at(-1), {
    channel: 'update:available',
    payload: { version: '4.0.0' },
  });
});

test('missing updater emits an error event instead of leaving checking state stuck', async () => {
  const ipcMain = makeIpcMain();
  const window = makeWindow();
  initAutoUpdater(ipcMain, window, { autoUpdater: null });

  const result = await ipcMain.handlers.get('update:check')({});

  assert.equal(result.ok, false);
  assert.equal(result.reason, 'updater-not-installed');
  assert.equal(window.sent.at(-1).channel, 'update:error');
});

function executePreload(isMainFrame) {
  const exposed = new Map();
  const invocations = [];
  const source = fs.readFileSync(path.join(__dirname, '..', 'preload.js'), 'utf8');
  const ipcRenderer = {
    invoke: async (channel, ...args) => {
      invocations.push({ channel, args });
      return { ok: true };
    },
    on: () => {},
    removeListener: () => {},
  };
  const context = {
    require(moduleName) {
      assert.equal(moduleName, 'electron');
      return {
        contextBridge: {
          exposeInMainWorld: (name, value) => exposed.set(name, value),
        },
        ipcRenderer,
      };
    },
    process: {
      env: {
        HORARY_PORT: '61234',
        APP_IS_PACKAGED: '1',
      },
      isMainFrame,
    },
    console,
    setTimeout,
    clearTimeout,
    URL,
  };
  vm.runInNewContext(source, context, { filename: 'preload.js' });
  return { exposed, invocations };
}

test('preload bridge is exposed only to the main frame and routes sensitive calls through IPC', async () => {
  const child = executePreload(false);
  assert.equal(child.exposed.size, 0);
  const unknownFrame = executePreload(undefined);
  assert.equal(unknownFrame.exposed.size, 0);

  const main = executePreload(true);
  assert.equal(main.exposed.get('API_BASE_URL'), 'http://127.0.0.1:61234');
  assert.equal(main.exposed.get('IS_PACKAGED'), true);
  const api = main.exposed.get('electronAPI');
  assert.equal(Object.isFrozen(api), true);
  await api.openPayPalCheckout('https://attacker.example/override');
  await api.openExternal('https://example.com');
  await api.exportReport({ html: '<p>safe</p>' });
  assert.deepEqual(main.invocations.map((entry) => entry.channel), [
    'license:open-paypal-checkout',
    'shell:open-external',
    'report:export',
  ]);
  assert.deepEqual(main.invocations[0].args, []);
});

test('main process source retains smoke, redirect, IPC, watchdog, and fatal-exit gates', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const indexHtml = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  const astroClockSource = fs.readFileSync(
    path.join(__dirname, '..', 'src', 'features', 'astroclock', 'AstroClock.jsx'),
    'utf8',
  );

  assert.match(source, /VOX_STELLA_SMOKE_TEST/);
  assert.match(source, /VOX_STELLA_EXPECTED_COMMIT/);
  assert.match(source, /VOX_STELLA_SMOKE_RESULT_PATH/);
  assert.match(source, /licensePublicKeySha256/);
  assert.match(source, /throw new Error\('Packaged licensing module is unavailable'\)/);
  assert.match(source, /throw new Error\('Packaged backend executable is missing'\)/);
  assert.match(source, /Packaged device identity could not be derived/);
  assert.match(source, /invalid_instance_proof/);
  assert.match(source, /recoverUnresponsiveBackend\('health-probe-failures'\)/);
  assert.match(source, /registerTrustedIpcHandler\('license:open-paypal-checkout', async \(\) =>/);
  assert.match(source, /registerTrustedIpcHandler\('report:export'/);
  assert.match(source, /webContents\.on\('will-redirect'/);
  assert.match(source, /terminateApplication\('uncaughtException'/);
  assert.match(indexHtml, /script-src 'self'/);
  assert.doesNotMatch(indexHtml, /script-src[^"]*paypal/i);
  assert.doesNotMatch(astroClockSource, /window\.open\(\s*['"]{2}\s*,\s*['"]_blank['"]/);
  assert.ok(
    source.indexOf('backendProc = await startInitialBackend(logDir);') <
      source.indexOf('await createWindow();'),
    'packaged backend readiness must be established before renderer creation',
  );
});

test('release smoke and packaging scripts pin artifact and updater identity', () => {
  const smokeSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'scripts', 'test-packaged-app.ps1'),
    'utf8',
  );
  const packageSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'package-app-new.bat'),
    'utf8',
  );

  assert.match(smokeSource, /\^owner:\\s\*aziz13-coder/);
  assert.match(smokeSource, /\^repo:\\s\*VoxStella_1/);
  assert.match(smokeSource, /System\.Diagnostics\.ProcessStartInfo/);
  assert.match(smokeSource, /if \(\$process\.ExitCode -ne 0\)/);
  assert.doesNotMatch(smokeSource, /Start-Process -FilePath/);
  assert.doesNotMatch(smokeSource, /\$null -ne \$reportedExitCode/);
  assert.match(smokeSource, /Test-Path -LiteralPath \$resultPath -PathType Leaf/);
  assert.match(
    packageSource,
    /VoxStella-Setup-%VOX_STELLA_BUILD_VERSION%\.exe/,
  );
  assert.match(
    packageSource,
    /build-logs\\toolchains\\node-v22\.23\.1-win-x64/,
  );
  assert.match(packageSource, /set "PATH=%LOCAL_NODE_DIR%;%PATH%"/);
  assert.doesNotMatch(packageSource, /VoxStella-Setup\*\.exe/);
  assert.doesNotMatch(packageSource, /dir \/b \/o:d "%OUT_DIR%\\\*\.exe"/);
});
